const subdirList = document.getElementById('subdir-list');
const homeStatus = document.getElementById('home-status');
const reloadButton = document.getElementById('reload-subdirs');

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

function renderSubdirectories(subdirectories) {
  subdirList.innerHTML = '';

  subdirectories.forEach((name) => {
    const li = document.createElement('li');
    const link = document.createElement('a');
    link.href = `/viewer?subdir=${encodeURIComponent(name)}`;
    link.textContent = name;
    li.appendChild(link);
    subdirList.appendChild(li);
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
