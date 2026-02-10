const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const subdirSelect = document.getElementById('subdir-select');
const reloadSubdirsBtn = document.getElementById('reload-subdirs');
const imageList = document.getElementById('image-list');
const mainImage = document.getElementById('main-image');
const emptyMessage = document.getElementById('empty-message');
const status = document.getElementById('status');
const mainPane = document.querySelector('.main');

const sidebarResizer = document.getElementById('sidebar-resizer');

const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 720;
const SIDEBAR_DEFAULT_WIDTH = 320;
let sidebarWidth = SIDEBAR_DEFAULT_WIDTH;

function applySidebarWidth(width) {
  const clampedWidth = Math.min(
    SIDEBAR_MAX_WIDTH,
    Math.max(SIDEBAR_MIN_WIDTH, width)
  );
  sidebarWidth = clampedWidth;
  document.querySelector('.app').style.setProperty('--sidebar-width', `${clampedWidth}px`);
}

let images = [];
let currentSubdir = '';
let currentIndex = -1;

toggleSidebarBtn.addEventListener('click', () => {
  const isCollapsed = sidebar.classList.toggle('collapsed');

  if (!isCollapsed) {
    applySidebarWidth(sidebarWidth);
  }
});

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function setStatus(message) {
  status.textContent = message;
}

function encodePathSegment(value) {
  return value
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
}

function renderImageList() {
  imageList.innerHTML = '';

  images.forEach((imageName, index) => {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.textContent = imageName;
    if (index === currentIndex) {
      button.classList.add('active');
    }
    button.addEventListener('click', () => showImage(index));
    li.appendChild(button);
    imageList.appendChild(li);
  });
}

function showImage(index) {
  if (index < 0 || index >= images.length) {
    return;
  }

  currentIndex = index;
  const imageName = images[index];
  const encodedSubdir = encodePathSegment(currentSubdir);
  const encodedImage = encodePathSegment(imageName);
  mainImage.src = `/api/image/${encodedSubdir}/${encodedImage}`;
  mainImage.style.display = 'block';
  emptyMessage.style.display = 'none';
  setStatus(`${currentIndex + 1} / ${images.length}: ${imageName}`);
  renderImageList();
}

async function loadImages(subdir) {
  currentSubdir = subdir;
  currentIndex = -1;
  mainImage.removeAttribute('src');
  mainImage.style.display = 'none';
  emptyMessage.style.display = 'grid';

  try {
    const data = await fetchJson(`/api/images/${encodePathSegment(subdir)}`);
    images = data.images;
    renderImageList();

    if (images.length > 0) {
      showImage(0);
    } else {
      setStatus('画像が見つかりません。');
    }
  } catch (error) {
    images = [];
    renderImageList();
    setStatus(`画像一覧の取得に失敗しました: ${error.message}`);
  }
}

async function refreshSubdirectories(preferredSubdir = '') {
  const hadCurrentSubdir = Boolean(preferredSubdir);
  reloadSubdirsBtn.disabled = true;

  try {
    const data = await fetchJson('/api/subdirectories');
    const subdirectories = data.subdirectories;

    if (subdirectories.length === 0) {
      subdirSelect.innerHTML = '';
      subdirSelect.disabled = true;
      images = [];
      currentSubdir = '';
      currentIndex = -1;
      renderImageList();
      mainImage.removeAttribute('src');
      mainImage.style.display = 'none';
      emptyMessage.style.display = 'grid';
      setStatus('サブディレクトリがありません。');
      return;
    }

    const nextSubdir =
      preferredSubdir && subdirectories.includes(preferredSubdir)
        ? preferredSubdir
        : subdirectories[0];

    subdirSelect.innerHTML = subdirectories
      .map((name) => `<option value="${name}">${name}</option>`)
      .join('');
    subdirSelect.value = nextSubdir;
    subdirSelect.disabled = false;

    await loadImages(nextSubdir);

    if (hadCurrentSubdir && preferredSubdir !== nextSubdir) {
      setStatus(`フォルダ「${preferredSubdir}」が見つからなかったため「${nextSubdir}」を表示しています。`);
    }
  } catch (error) {
    setStatus(`サブディレクトリ一覧の取得に失敗しました: ${error.message}`);
  } finally {
    reloadSubdirsBtn.disabled = false;
  }
}

async function init() {
  setStatus('読み込み中...');

  subdirSelect.addEventListener('change', (event) => {
    loadImages(event.target.value);
  });

  reloadSubdirsBtn.addEventListener('click', () => {
    refreshSubdirectories(subdirSelect.value || currentSubdir);
  });

  await refreshSubdirectories();
}

document.addEventListener('keydown', (event) => {
  if (images.length === 0) {
    return;
  }

  if (event.key === 'ArrowRight') {
    showImage((currentIndex + 1) % images.length);
  }

  if (event.key === 'ArrowLeft') {
    showImage((currentIndex - 1 + images.length) % images.length);
  }
});

if (mainPane) {
  mainPane.addEventListener(
    'wheel',
    (event) => {
      if (images.length === 0 || event.deltaY === 0) {
        return;
      }

      event.preventDefault();

      if (event.deltaY > 0) {
        showImage((currentIndex + 1) % images.length);
        return;
      }

      showImage((currentIndex - 1 + images.length) % images.length);
    },
    { passive: false }
  );
}

init();


if (sidebarResizer) {
  const stopResizing = () => {
    sidebarResizer.classList.remove('dragging');
    document.body.style.userSelect = '';
    window.removeEventListener('mousemove', onResize);
    window.removeEventListener('mouseup', stopResizing);
  };

  const onResize = (event) => {
    if (sidebar.classList.contains('collapsed')) {
      return;
    }

    applySidebarWidth(event.clientX);
  };

  sidebarResizer.addEventListener('mousedown', (event) => {
    if (sidebar.classList.contains('collapsed')) {
      return;
    }

    event.preventDefault();
    sidebarResizer.classList.add('dragging');
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', onResize);
    window.addEventListener('mouseup', stopResizing);
  });
}

applySidebarWidth(SIDEBAR_DEFAULT_WIDTH);
