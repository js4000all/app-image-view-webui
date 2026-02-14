const selectedSubdir = document.getElementById('selected-subdir');
const imageIndex = document.getElementById('image-index');
const imageName = document.getElementById('image-name');
const deleteCurrentImageButton = document.getElementById('delete-current-image');
const mainImage = document.getElementById('main-image');
const emptyMessage = document.getElementById('empty-message');
const status = document.getElementById('status');
const mainPane = document.querySelector('.main');

let images = [];
let currentDirectory = null;
let currentIndex = -1;

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

function updateFooter() {
  if (currentDirectory) {
    selectedSubdir.textContent = `フォルダ: ${currentDirectory.name}`;
  } else {
    selectedSubdir.textContent = '';
  }

  if (currentIndex < 0 || currentIndex >= images.length) {
    imageIndex.textContent = '0 / 0';
    imageName.textContent = '';
    deleteCurrentImageButton.disabled = true;
    return;
  }

  imageIndex.textContent = `${currentIndex + 1} / ${images.length}`;
  imageName.textContent = images[currentIndex].name;
  deleteCurrentImageButton.disabled = false;
}

async function reloadImagesAfterDelete() {
  const previousFileId = images[currentIndex]?.file_id || '';
  const data = await fetchJson(`/api/images/${encodeURIComponent(currentDirectory.directory_id)}`);
  images = data.images;

  if (images.length === 0) {
    currentIndex = -1;
    mainImage.removeAttribute('src');
    mainImage.style.display = 'none';
    emptyMessage.style.display = 'grid';
    updateFooter();
    setStatus('画像が見つかりません。');
    return;
  }

  const targetIndex = images.findIndex((image) => image.file_id === previousFileId);
  if (targetIndex >= 0) {
    showImage(targetIndex);
    return;
  }

  showImage(Math.min(currentIndex, images.length - 1));
}

async function deleteImage(image) {
  if (!currentDirectory) {
    return;
  }

  try {
    const response = await fetch(`/api/image/${encodeURIComponent(image.file_id)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    await reloadImagesAfterDelete();
    setStatus(`画像を削除しました: ${image.name}`);
  } catch (error) {
    setStatus(`画像の削除に失敗しました: ${error.message}`);
  }
}

function showImage(index) {
  if (index < 0 || index >= images.length) {
    return;
  }

  currentIndex = index;
  const image = images[index];
  mainImage.src = `/api/image/${encodeURIComponent(image.file_id)}`;
  mainImage.style.display = 'block';
  emptyMessage.style.display = 'none';
  updateFooter();
  setStatus(`${currentIndex + 1} / ${images.length}: ${image.name}`);
}

async function resolveInitialDirectory(requestedDirectoryId) {
  const data = await fetchJson('/api/subdirectories');
  const subdirectories = data.subdirectories;

  if (subdirectories.length === 0) {
    throw new Error('サブディレクトリがありません。');
  }

  if (!requestedDirectoryId) {
    return subdirectories[0];
  }

  const matched = subdirectories.find((subdirectory) => subdirectory.directory_id === requestedDirectoryId);
  if (matched) {
    return matched;
  }

  throw new Error('指定されたフォルダが見つかりません。');
}

async function loadImages(directory) {
  currentDirectory = directory;
  currentIndex = -1;
  updateFooter();
  mainImage.removeAttribute('src');
  mainImage.style.display = 'none';
  emptyMessage.style.display = 'grid';

  try {
    const data = await fetchJson(`/api/images/${encodeURIComponent(directory.directory_id)}`);
    images = data.images;

    if (images.length > 0) {
      showImage(0);
    } else {
      updateFooter();
      setStatus('画像が見つかりません。');
    }
  } catch (error) {
    images = [];
    updateFooter();
    setStatus(`画像一覧の取得に失敗しました: ${error.message}`);
  }
}

async function init() {
  setStatus('読み込み中...');

  try {
    const params = new URLSearchParams(window.location.search);
    const requestedDirectoryId = params.get('directory_id') || '';
    const directory = await resolveInitialDirectory(requestedDirectoryId);
    await loadImages(directory);
  } catch (error) {
    setStatus(error.message);
    selectedSubdir.textContent = '';
    images = [];
    currentIndex = -1;
    updateFooter();
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

deleteCurrentImageButton.addEventListener('click', async () => {
  if (currentIndex < 0 || currentIndex >= images.length) {
    return;
  }

  await deleteImage(images[currentIndex]);
});

updateFooter();
init();
