(function () {
    'use strict';

    function filterDatasetsByType(type) {
        const sel = document.getElementById('dataset_select');
        if (!sel) return;
        let firstEnabled = null;
        for (let i = 0; i < sel.options.length; i++) {
            const opt = sel.options[i];
            const types = (opt.getAttribute('data-types') || '').split(',').map(s => s.trim()).filter(Boolean);
            const compatible = types.length === 0 || types.includes(type);
            opt.disabled = !compatible && opt.value !== 'random';
            if (!compatible && opt.value !== 'random') {
                opt.style.display = 'none';
            } else {
                opt.style.display = '';
                if (!firstEnabled && !opt.disabled) firstEnabled = opt.value;
            }
        }
        if (sel.options[sel.selectedIndex] && sel.options[sel.selectedIndex].disabled) {
            if (firstEnabled) sel.value = firstEnabled;
            else sel.value = 'random';
            applyPreview(sel.value);
        }
    }

    function pickRecord(idx) {
        if (!excelData || excelData.length === 0) return null;
        if (idx === 'random' || idx === null) {
            return excelData[Math.floor(Math.random() * excelData.length)];
        }
        const i = parseInt(idx, 10);
        if (!Number.isFinite(i) || i < 0 || i >= excelData.length) {
            return excelData[Math.floor(Math.random() * excelData.length)];
        }
        return excelData[i];
    }

    function applyPreview(idx) {
        const record = pickRecord(idx);
        if (!record) {
            window._selectedExcelRecord = null;
            return;
        }
        window._selectedExcelRecord = record;
        // Normalize record: prefer `record.fields` (server-normalized) then `record` top-level
        const src = (record && record.fields && typeof record.fields === 'object') ? record.fields : record || {};
        const mapping = {
            'BSN_preview': src.BSN || src.Burgerservicenr || src.bsn || '',
            'Geb_datum_preview': src.Geb_datum || src.Geboortedat || src.Geboortedatum || '',
            'Naam_preview': src.Naam || src.naam || '',
            'Loonheffingennummer_preview': src.Loonheffingennr || src.Loonheffingennummer || src.Loonheffingennr || '',
            'Rekeningnummer_preview': src.Iban || src.Rekeningnummer || src.IBAN || '',
            'BIC_preview': src.Bic || src.BIC || ''
        };
        Object.keys(mapping).forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            el.value = mapping[id] === undefined || mapping[id] === null ? '' : String(mapping[id]);
        });
        try { console.debug('applyPreview mapping', mapping, 'record:', record); } catch (e) {}
    }

    function enableEditing() {
        const record = window._selectedExcelRecord || pickRecord(document.getElementById('dataset_select').value);
        document.getElementById('editable-fields').classList.remove('d-none');
        document.getElementById('dataset-preview-card').querySelectorAll('.preview-input').forEach(n => n.classList.add('d-none'));
        document.getElementById('enable-editing').classList.add('d-none');
        document.getElementById('cancel-editing').classList.remove('d-none');

        const mapping = [ ['BSN','BSN_edit'], ['Geb_datum','Geb_datum_edit'], ['Naam','Naam_edit'], ['Loonheffingennr','Loonheffingennr_edit'], ['Iban','Rekeningnummer_edit'], ['Bic','BIC_edit'] ];
        mapping.forEach(([field, editId]) => {
            const el = document.getElementById(editId);
            if (!el) return;
            // Prefer common keys, fall back to Burgerservicenr
            let val = '';
            if (record) {
                const recFields = (record.fields && typeof record.fields === 'object') ? record.fields : record;
                // Only use values from the selected record's row. Do not inject global demo defaults here.
                val = recFields[field] || recFields['Burgerservicenr'] || recFields['Rekeningnummer'] || recFields['IBAN'] || '';
            }
            el.value = val === undefined ? '' : val;
        });

        document.querySelectorAll('.editable-input').forEach(inp => {
            inp.addEventListener('input', function () {
                const field = this.name === 'Loonheffingennummer' ? 'Loonheffingennr' : this.name;
                // mark editing visually if needed; badges removed in template
            });
        });
        const sel = document.getElementById('dataset_select'); if (sel) sel.disabled = true;
    }

    function cancelEditing() {
        document.getElementById('editable-fields').classList.add('d-none');
        document.getElementById('dataset-preview-card').querySelectorAll('.preview-input').forEach(n => n.classList.remove('d-none'));
        document.getElementById('enable-editing').classList.remove('d-none');
        document.getElementById('cancel-editing').classList.add('d-none');
        const map = [ ['BSN_preview','BSN_edit'], ['Geb_datum_preview','Geb_datum_edit'], ['Naam_preview','Naam_edit'], ['Loonheffingennummer_preview','Loonheffingennr_edit'], ['Rekeningnummer_preview','Rekeningnummer_edit'], ['BIC_preview','BIC_edit'] ];
        map.forEach(([p,e]) => {
            const pv = document.getElementById(p);
            const ev = document.getElementById(e);
            if (pv && ev) ev.value = pv.value;
        });
        const sel = document.getElementById('dataset_select'); if (sel) sel.disabled = false;
    }

    document.addEventListener('DOMContentLoaded', function () {
        const sel = document.getElementById('dataset_select');
        if (!sel) return;
        applyPreview(sel.value || 'random');
        const typeSel = document.getElementById('aanvraag_type');
        if (typeSel) filterDatasetsByType(typeSel.value);
        if (typeSel) typeSel.addEventListener('change', function (ev) { filterDatasetsByType(ev.target.value); });
        sel.addEventListener('change', function (ev) {
            applyPreview(ev.target.value);
        });
        const btn = document.getElementById('enable-editing');
        if (btn) btn.addEventListener('click', enableEditing);
        const cancel = document.getElementById('cancel-editing');
        if (cancel) cancel.addEventListener('click', cancelEditing);
    });

})();
