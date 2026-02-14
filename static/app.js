const sidebar = document.getElementById('sidebar');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const selectedSubdir = document.getElementById('selected-subdir');
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
    const row = document.createElement('div');
    row.classList.add('image-list-row');

    const button = document.createElement('button');
    button.type = 'button';
    button.classList.add('image-item-button');
    button.textContent = imageName;
    if (index === currentIndex) {
      button.classList.add('active');
    }
    button.addEventListener('click', () => showImage(index));

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.classList.add('image-delete-button');
    deleteButton.textContent = '削除';
    deleteButton.setAttribute('aria-label', `画像「${imageName}」を削除`);
    deleteButton.addEventListener('click', async (event) => {
      event.stopPropagation();
      await deleteImage(imageName);
    });

    row.appendChild(button);
    row.appendChild(deleteButton);
    li.appendChild(row);
    imageList.appendChild(li);
  });
}

async function reloadImagesAfterDelete() {
  const previousImageName = images[currentIndex] || '';
  const data = await fetchJson(`/api/images/${encodePathSegment(currentSubdir)}`);
  images = data.images;
  renderImageList();

  if (images.length === 0) {
    currentIndex = -1;
    mainImage.removeAttribute('src');
    mainImage.style.display = 'none';
    emptyMessage.style.display = 'grid';
    setStatus('画像が見つかりません。');
    return;
  }

  const targetIndex = images.indexOf(previousImageName);
  if (targetIndex >= 0) {
    showImage(targetIndex);
    return;
  }

  showImage(Math.min(currentIndex, images.length - 1));
}

async function deleteImage(imageName) {
  if (!currentSubdir) {
    return;
  }

  try {
    const encodedSubdir = encodePathSegment(currentSubdir);
    const encodedImage = encodePathSegment(imageName);
    const response = await fetch(`/api/image/${encodedSubdir}/${encodedImage}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await reloadImagesAfterDelete();
    setStatus(`画像を削除しました: ${imageName}`);
  } catch (error) {
    setStatus(`画像の削除に失敗しました: ${error.message}`);
  }
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

async function resolveInitialSubdirectory(rawSubdir) {
  const data = await fetchJson('/api/subdirectories');
  const subdirectories = data.subdirectories;

  if (subdirectories.length === 0) {
    throw new Error('サブディレクトリがありません。');
  }

  if (!rawSubdir) {
    return subdirectories[0];
  }

  if (subdirectories.includes(rawSubdir)) {
    return rawSubdir;
  }

  throw new Error(`フォルダ「${rawSubdir}」が見つかりません。`);
}

async function loadImages(subdir) {
  currentSubdir = subdir;
  currentIndex = -1;
  selectedSubdir.textContent = `フォルダ: ${subdir}`;
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
    const params = new URLSearchParams(window.location.search);
    const requestedSubdir = params.get('subdir') || '';
    const subdir = await resolveInitialSubdirectory(requestedSubdir);
    await loadImages(subdir);
  } catch (error) {
    setStatus(error.message);
    selectedSubdir.textContent = '';
    images = [];
    renderImageList();
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
