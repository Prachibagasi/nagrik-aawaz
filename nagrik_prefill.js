/**

 * Shared prefill for Nagrik Awaaz → dummy department portals.

 * Data is passed via URL ?nagrik_prefill=... (cross-origin safe) or sessionStorage (same origin).

 */

(function () {

  var KEY = 'nagrik_dept_prefill';



  function decodePrefillParam(encoded) {

    return JSON.parse(decodeURIComponent(escape(atob(encoded))));

  }



  function readPrefillData() {

    try {

      var params = new URLSearchParams(window.location.search);

      var enc = params.get('nagrik_prefill');

      if (enc) {

        return decodePrefillParam(enc);

      }

    } catch (e) {

      console.warn('Nagrik URL prefill decode failed', e);

    }

    try {

      var raw = sessionStorage.getItem(KEY);

      if (raw) {

        sessionStorage.removeItem(KEY);

        return JSON.parse(raw);

      }

    } catch (e2) {

      console.warn('Nagrik session prefill failed', e2);

    }

    return null;

  }



  function setVal(id, value) {

    if (value == null || value === '') return;

    var el = document.getElementById(id);

    if (el) el.value = value;

  }



  function selectOption(selectId, wanted) {

    if (!wanted) return;

    var sel = document.getElementById(selectId);

    if (!sel) return;

    var w = String(wanted).toLowerCase();

    for (var i = 0; i < sel.options.length; i++) {

      var opt = sel.options[i];

      if (opt.text === wanted || opt.value === wanted) {

        sel.selectedIndex = i;

        return;

      }

      if (opt.text.toLowerCase().indexOf(w) >= 0 || w.indexOf(opt.text.toLowerCase()) >= 0) {

        sel.selectedIndex = i;

        return;

      }

    }

    if (sel.options.length > 1) {

      sel.selectedIndex = sel.options.length - 1;

    }

  }



  function showBanner(text) {

    var bar = document.createElement('div');

    bar.setAttribute('role', 'status');

    bar.style.cssText =

      'position:fixed;top:0;left:0;right:0;z-index:99999;background:#1b2a4a;color:#fff;padding:12px 16px;font:600 14px/1.4 sans-serif;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.2)';

    bar.textContent = text;

    document.body.prepend(bar);

  }



  function applyPrefill(data) {

    var p = data.form_payload || data;

    var key = p.portal_key || data.portal_key || data.dept;

    var cid = p.nagrik_complaint_id || data.complaint_id || '';



    if (key === 'pwd') {

      setVal('f-name', p.name);

      setVal('f-mobile', p.mobile);

      setVal('f-email', p.email);

      selectOption('f-district', p.district);

      selectOption('f-category', p.category);

      setVal('f-location', p.location || p.district);

      setVal('f-desc', p.description);

    } else if (key === 'bijli') {

      setVal('accountNo', p.accountNo || '');

      setVal('consumerName', p.name);

      setVal('district', p.district);

      selectOption('complaintType', p.category);

      setVal('description', p.description);

      setVal('mobile', p.mobile);

      setVal('email', p.email);

    } else if (key === 'jal') {

      setVal('fc_accountNo', p.accountNo || 'N/A');

      setVal('fc_name', p.name);

      setVal('fc_mobile', p.mobile);

      selectOption('fc_zone', p.zone || p.district);

      selectOption('fc_type', p.type || p.category);

      setVal('fc_desc', p.description);

      if (typeof openDashboard === 'function') openDashboard();

      if (typeof switchTab === 'function') {

        var btn = document.querySelector("button[onclick*=\"tab-file\"]");

        switchTab(btn, 'tab-file');

      }

    } else if (key === 'shiksha') {

      setVal('cf_name', p.name);

      setVal('cf_mobile', p.mobile);

      setVal('cf_email', p.email);

      selectOption('cf_cat', p.category);

      selectOption('cf_dist', p.district);

      setVal('cf_school', p.school || '');

      setVal('cf_desc', p.description);

      if (typeof openComplaintDashboard === 'function') openComplaintDashboard();

    }



    if (cid) {

      showBanner('Routed from Nagrik Awaaz — ' + cid + ' · Form pre-filled with your details');

    }

  }



  window.applyNagrikDeptPrefill = applyPrefill;



  function boot() {

    var data = readPrefillData();

    if (!data) return;

    if (data.portal_key === 'jal' || data.portal_key === 'shiksha' || (data.form_payload && (data.form_payload.portal_key === 'jal' || data.form_payload.portal_key === 'shiksha'))) {

      setTimeout(function () { applyPrefill(data); }, 400);

    } else {

      applyPrefill(data);

    }

  }



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', boot);

  } else {

    boot();

  }

})();


