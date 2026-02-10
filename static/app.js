const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const subdirSelect = document.getElementById('subdir-select');
const imageList = document.getElementById('image-list');
const mainImage = document.getElementById('main-image');
const emptyMessage = document.getElementById('empty-message');
const status = document.getElementById('status');
const mainPane = document.querySelector('.main');

let images = [];
let currentSubdir = '';
let currentIndex = -1;

toggleSidebarBtn.addEventListener('click', () => {
  sidebar.classList.toggle('collapsed');
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

async function init() {
  setStatus('読み込み中...');

  try {
    const data = await fetchJson('/api/subdirectories');

    if (data.subdirectories.length === 0) {
      setStatus('サブディレクトリがありません。');
      subdirSelect.disabled = true;
      return;
    }

    subdirSelect.innerHTML = data.subdirectories
      .map((name) => `<option value="${name}">${name}</option>`)
      .join('');

    subdirSelect.addEventListener('change', (event) => {
      loadImages(event.target.value);
    });

    await loadImages(subdirSelect.value);
  } catch (error) {
    setStatus(`初期化に失敗しました: ${error.message}`);
  }
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
