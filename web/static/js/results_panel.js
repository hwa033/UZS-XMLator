// Shared Results Panel handlers and refresh
(function() {
  function freshElement(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const clone = el.cloneNode(true);
    el.replaceWith(clone);
    return clone;
  }
  function updateSelectionState() {
    const downloadBtn = document.getElementById('download-selected-btn');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const checkboxes = Array.from(document.querySelectorAll('.generated-select'));
    const anyChecked = checkboxes.some(cb => cb.checked);
    if (downloadBtn) downloadBtn.disabled = !anyChecked;
    if (deleteBtn) deleteBtn.disabled = !anyChecked;
    checkboxes.forEach(cb => {
      const item = cb.closest('.generated-item');
      if (item) item.classList.toggle('selected', cb.checked);
    });
  }

  async function downloadSelectedAsZip(filenames) {
    const zipSpinner = document.getElementById('zipSpinner');
    try {
      if (zipSpinner) zipSpinner.style.display = '';
      const zipProgressWrap = document.getElementById('zipProgressWrap');
      const zipProgressText = document.getElementById('zipProgressText');
      if (zipProgressWrap && zipProgressText) {
        zipProgressWrap.style.display = '';
        zipProgressText.textContent = '0%';
      }
      const resp = await fetch('/resultaten/download-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filenames: filenames })
      });
      if (!resp.ok) {
        alert('Fout bij maken van ZIP: ' + await resp.text());
        return;
      }
      const reader = resp.body.getReader();
      const contentLength = +resp.headers.get('Content-Length') || 0;
      let received = 0;
      let chunks = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.length;
        if (zipProgressText && contentLength) {
          const percent = Math.round((received / contentLength) * 100);
          zipProgressText.textContent = percent + '%';
        }
      }
      if (zipProgressText) zipProgressText.textContent = '100%';
      const blob = new Blob(chunks);
      let zipName = 'selected_files.zip';
      const cd = resp.headers.get('Content-Disposition');
      if (cd) {
        const m = cd.match(/filename\*=UTF-8''([^;\n\r]+)/) || cd.match(/filename="?([^";]+)"?/);
        if (m && m[1]) zipName = decodeURIComponent(m[1]);
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = zipName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (err) {
      alert('Fout bij downloaden: ' + err);
    } finally {
      if (zipSpinner) zipSpinner.style.display = 'none';
      const zipProgressWrap = document.getElementById('zipProgressWrap');
      if (zipProgressWrap) zipProgressWrap.style.display = 'none';
    }
  }

  window.refreshResultsList = function refreshResultsList() {
    fetch('/resultaten/fragment')
      .then(resp => resp.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newResults = doc.getElementById('results-panel');
        const oldResults = document.getElementById('results-panel');
        if (newResults && oldResults) {
          oldResults.innerHTML = newResults.innerHTML;
          if (newResults.dataset) {
            oldResults.dataset.shown = newResults.dataset.shown || '0';
            oldResults.dataset.total = newResults.dataset.total || '0';
          }

          const availableCount = document.getElementById('available-count');
          const totalCount = newResults.dataset ? newResults.dataset.total : null;
          if (availableCount && totalCount !== null) {
            availableCount.textContent = `${totalCount} bestand(en) beschikbaar voor download`;
          }

          initResultsPanelHandlers();
        }
      })
      .catch(err => console.error('Error refreshing results:', err));
  };

  window.initResultsPanelHandlers = function initResultsPanelHandlers() {
    const list = document.getElementById('generatedList');
    const downloadBtn = freshElement('download-selected-btn');
    const deleteBtn = freshElement('delete-selected-btn');
    const selectAll = freshElement('select-all-generated');

    const refreshBtn = freshElement('refresh-results-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function () {
        window.refreshResultsList();
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener('click', function () {
        const checked = Array.from(document.querySelectorAll('.generated-select:checked'));
        const filenames = checked.map(cb => cb.getAttribute('data-file')).filter(Boolean);
        if (filenames.length === 0) return;
        
        const deleteSpinner = document.getElementById('deleteSpinner');
        if (deleteSpinner) deleteSpinner.style.display = '';
        deleteBtn.disabled = true;
        
        fetch('/resultaten/delete-selected', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filenames: filenames })
        })
        .then(resp => resp.json())
        .then(data => {
          if (data.success) {
            // Geen alert; stil vernieuwen met optionele toast
            if (window.flashMessage) {
              window.flashMessage(`${data.deleted} bestand(en) verwijderd.`);
            }
            if (window.refreshResultsList) window.refreshResultsList();
          } else {
            alert('Fout bij verwijderen: ' + (data.error || 'Onbekende fout'));
          }
        })
        .catch(err => {
          alert('Fout bij verwijderen: ' + err);
        })
        .finally(() => {
          if (deleteSpinner) deleteSpinner.style.display = 'none';
          deleteBtn.disabled = false;
        });
      });
    }

    if (list) {
      list.addEventListener('change', function (ev) {
        if (ev.target && ev.target.classList.contains('generated-select')) updateSelectionState();
      });
    }

    if (selectAll) {
      selectAll.addEventListener('change', function () {
        const checkboxes = Array.from(document.querySelectorAll('.generated-select'));
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
        updateSelectionState();
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener('click', function () {
        const checked = Array.from(document.querySelectorAll('.generated-select:checked'));
        const filenames = checked.map(cb => cb.getAttribute('data-file')).filter(Boolean);
        if (filenames.length > 0) downloadSelectedAsZip(filenames);
      });
    }

    updateSelectionState();
  };
})();
