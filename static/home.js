const subdirList = document.getElementById('subdir-list');
const homeStatus = document.getElementById('home-status');
const reloadButton = document.getElementById('reload-subdirs');

let thumbnailObserver;

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function putJson(url, body) {
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (response.ok) {
    return response.json();
  }

  const error = new Error(`HTTP ${response.status}`);
  error.status = response.status;
  throw error;
}

function setStatus(message) {
  homeStatus.textContent = message;
}

function addEmptyThumbnailMessage(thumbnailContainer) {
  thumbnailContainer.innerHTML = '';
  const emptyMessage = document.createElement('p');
  emptyMessage.className = 'subdir-no-images';
  emptyMessage.textContent = '画像なし';
  thumbnailContainer.appendChild(emptyMessage);
}

function createThumbnailElement(subdirectoryName, image) {
  const wrapper = document.createElement('div');
  wrapper.className = 'subdir-thumb-slot';

  const img = document.createElement('img');
  img.className = 'subdir-thumb';
  img.loading = 'lazy';
  img.decoding = 'async';
  img.src = `/api/image/${encodeURIComponent(image.file_id)}`;
  img.alt = `${subdirectoryName} のサムネイル ${image.name}`;
  img.onerror = () => {
    img.classList.add('is-hidden');
    wrapper.classList.add('is-fallback');
  };

  wrapper.appendChild(img);
  return wrapper;
}

async function loadSubdirectoryThumbnails(card) {
  if (card.dataset.thumbnailsLoaded === 'true' || card.dataset.loadingThumbnails === 'true') {
    return;
  }

  card.dataset.loadingThumbnails = 'true';
  const directoryId = card.dataset.directoryId;
  const subdirectoryName = card.dataset.subdirectoryName;
  const thumbnailContainer = card.querySelector('.subdir-thumbs');

  try {
    const data = await fetchJson(`/api/images/${encodeURIComponent(directoryId)}`);
    const images = data.images.slice(0, 5);

    thumbnailContainer.innerHTML = '';

    if (images.length === 0) {
      addEmptyThumbnailMessage(thumbnailContainer);
    } else {
      images.forEach((image) => {
        thumbnailContainer.appendChild(createThumbnailElement(subdirectoryName, image));
      });
    }

    card.dataset.thumbnailsLoaded = 'true';
  } catch (_error) {
    addEmptyThumbnailMessage(thumbnailContainer);
    card.dataset.thumbnailsLoaded = 'true';
  } finally {
    delete card.dataset.loadingThumbnails;
  }
}

function observeCardThumbnails(card) {
  if (thumbnailObserver) {
    thumbnailObserver.observe(card);
    return;
  }

  // IntersectionObserver がない環境では描画後に順次ロードする。
  loadSubdirectoryThumbnails(card);
}

function setupThumbnailObserver() {
  if (thumbnailObserver) {
    thumbnailObserver.disconnect();
  }

  if ('IntersectionObserver' in window) {
    thumbnailObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const card = entry.target;
          loadSubdirectoryThumbnails(card);
          thumbnailObserver.unobserve(card);
        });
      },
      {
        root: null,
        rootMargin: '120px 0px',
        threshold: 0.1,
      },
    );
  } else {
    thumbnailObserver = null;
  }
}

function createSubdirectoryCard(subdirectory) {
  const li = document.createElement('li');

  const row = document.createElement('div');
  row.className = 'subdir-row';

  const link = document.createElement('a');
  link.className = 'subdir-card';
  link.href = `/viewer?directory_id=${encodeURIComponent(subdirectory.directory_id)}`;
  link.dataset.directoryId = subdirectory.directory_id;
  link.dataset.subdirectoryName = subdirectory.name;

  const meta = document.createElement('div');
  meta.className = 'subdir-meta';

  const title = document.createElement('p');
  title.className = 'subdir-name';
  title.textContent = subdirectory.name;
  meta.appendChild(title);

  const thumbs = document.createElement('div');
  thumbs.className = 'subdir-thumbs';

  const loadingMessage = document.createElement('p');
  loadingMessage.className = 'subdir-loading';
  loadingMessage.textContent = '画像を読み込み中...';
  thumbs.appendChild(loadingMessage);

  link.append(meta, thumbs);
  row.appendChild(link);

  const renameButton = document.createElement('button');
  renameButton.type = 'button';
  renameButton.className = 'subdir-rename-button';
  renameButton.textContent = '名前変更';
  renameButton.addEventListener('click', async () => {
    const newName = window.prompt('新しいディレクトリ名を入力してください。', subdirectory.name);
    if (newName === null) {
      return;
    }

    const trimmed = newName.trim();
    if (!trimmed || trimmed === subdirectory.name) {
      return;
    }

    renameButton.disabled = true;
    setStatus(`「${subdirectory.name}」を「${trimmed}」に変更中...`);

    try {
      await putJson(`/api/subdirectories/${encodeURIComponent(subdirectory.directory_id)}`, { new_name: trimmed });
      await refreshSubdirectories();
      setStatus(`「${subdirectory.name}」を「${trimmed}」に変更しました。`);
    } catch (error) {
      if (error.status === 400) {
        setStatus('ディレクトリ名の変更に失敗しました: 名前が不正です。');
      } else if (error.status === 409) {
        setStatus('ディレクトリ名の変更に失敗しました: 同名ディレクトリが既に存在します。');
      } else {
        setStatus(`ディレクトリ名の変更に失敗しました: ${error.message}`);
      }
    } finally {
      renameButton.disabled = false;
    }
  });

  row.appendChild(renameButton);
  li.appendChild(row);

  observeCardThumbnails(link);
  return li;
}

function renderSubdirectories(subdirectories) {
  subdirList.innerHTML = '';
  setupThumbnailObserver();

  subdirectories.forEach((subdirectory) => {
    subdirList.appendChild(createSubdirectoryCard(subdirectory));
  });
}

async function refreshSubdirectories() {
  reloadButton.disabled = true;
  setStatus('読み込み中...');

  try {
    const data = await fetchJson('/api/subdirectories');
    const subdirectories = data.subdirectories;

    if (subdirectories.length === 0) {
      renderSubdirectories([]);
      setStatus('サブディレクトリがありません。');
      return;
    }

    renderSubdirectories(subdirectories);
    setStatus(`${subdirectories.length} 件のサブディレクトリがあります。`);
  } catch (error) {
    setStatus(`サブディレクトリ一覧の取得に失敗しました: ${error.message}`);
  } finally {
    reloadButton.disabled = false;
  }
}

reloadButton.addEventListener('click', refreshSubdirectories);

refreshSubdirectories();
