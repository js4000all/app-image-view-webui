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

function setStatus(message) {
  homeStatus.textContent = message;
}

async function renameSubdirectory(oldName, newName) {
  const response = await fetch('/api/subdirectories/rename', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ old_name: oldName, new_name: newName }),
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.error === 'string') {
        message = payload.error;
      }
    } catch (_error) {
      // JSON 解析に失敗した場合は HTTP ステータスを表示する。
    }
    throw new Error(message);
  }

  return response.json();
}

function addEmptyThumbnailMessage(thumbnailContainer) {
  thumbnailContainer.innerHTML = '';
  const emptyMessage = document.createElement('p');
  emptyMessage.className = 'subdir-no-images';
  emptyMessage.textContent = '画像なし';
  thumbnailContainer.appendChild(emptyMessage);
}

function createThumbnailElement(subdirectory, filename) {
  const wrapper = document.createElement('div');
  wrapper.className = 'subdir-thumb-slot';

  const img = document.createElement('img');
  img.className = 'subdir-thumb';
  img.loading = 'lazy';
  img.decoding = 'async';
  img.src = `/api/image/${encodeURIComponent(subdirectory)}/${encodeURIComponent(filename)}`;
  img.alt = `${subdirectory} のサムネイル ${filename}`;
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
  const subdirectory = card.dataset.subdirectory;
  const thumbnailContainer = card.querySelector('.subdir-thumbs');

  try {
    const data = await fetchJson(`/api/images/${encodeURIComponent(subdirectory)}`);
    const images = data.images.slice(0, 5);

    thumbnailContainer.innerHTML = '';

    if (images.length === 0) {
      addEmptyThumbnailMessage(thumbnailContainer);
    } else {
      images.forEach((filename) => {
        thumbnailContainer.appendChild(createThumbnailElement(subdirectory, filename));
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

function createSubdirectoryCard(name) {
  const li = document.createElement('li');

  const card = document.createElement('div');
  card.className = 'subdir-card';

  const link = document.createElement('a');
  link.className = 'subdir-link';
  link.href = `/viewer?subdir=${encodeURIComponent(name)}`;
  link.dataset.subdirectory = name;

  const meta = document.createElement('div');
  meta.className = 'subdir-meta';

  const title = document.createElement('p');
  title.className = 'subdir-name';
  title.textContent = name;
  meta.appendChild(title);

  const thumbs = document.createElement('div');
  thumbs.className = 'subdir-thumbs';

  const loadingMessage = document.createElement('p');
  loadingMessage.className = 'subdir-loading';
  loadingMessage.textContent = '画像を読み込み中...';
  thumbs.appendChild(loadingMessage);

  link.append(meta, thumbs);
  card.appendChild(link);

  const actions = document.createElement('div');
  actions.className = 'subdir-actions';

  const renameInput = document.createElement('input');
  renameInput.type = 'text';
  renameInput.className = 'subdir-rename-input';
  renameInput.value = name;
  renameInput.setAttribute('aria-label', `${name} の新しいディレクトリ名`);

  const renameButton = document.createElement('button');
  renameButton.type = 'button';
  renameButton.className = 'subdir-rename-button';
  renameButton.textContent = '名前変更';

  renameButton.addEventListener('click', async () => {
    const newName = renameInput.value.trim();
    if (!newName) {
      setStatus('変更後のディレクトリ名を入力してください。');
      return;
    }

    if (newName === name) {
      setStatus('変更前と同じ名前です。');
      return;
    }

    renameButton.disabled = true;
    renameInput.disabled = true;

    try {
      await renameSubdirectory(name, newName);
      setStatus(`ディレクトリ名を ${name} から ${newName} に変更しました。`);
      await refreshSubdirectories();
    } catch (error) {
      setStatus(`ディレクトリ名の変更に失敗しました: ${error.message}`);
    } finally {
      renameButton.disabled = false;
      renameInput.disabled = false;
    }
  });

  actions.append(renameInput, renameButton);
  card.appendChild(actions);
  li.appendChild(card);

  observeCardThumbnails(link);
  return li;
}

function renderSubdirectories(subdirectories) {
  subdirList.innerHTML = '';
  setupThumbnailObserver();

  subdirectories.forEach((name) => {
    subdirList.appendChild(createSubdirectoryCard(name));
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
