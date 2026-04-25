// Resume quick preview modal — injected into tracked page
(function() {
    var added = false;
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.view-resume-btn');
        if (btn) {
            e.preventDefault();
            showResumePreview(btn.getAttribute('data-job-id'));
        }
    });

    window._resumeJobId = null;

    window.showResumePreview = async function(jobId) {
        var old = document.getElementById('resume-view-modal');
        if (old) old.remove();
        window._resumeJobId = jobId;

        var h = '<div id="resume-view-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);z-index:1000;display:flex;align-items:center;justify-content:center">';
        h += '<div id="resume-view-card" style="background:#fff;border-radius:12px;padding:0;max-width:700px;width:95%;box-shadow:0 8px 32px rgba(0,0,0,0.2)">';
        h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e0e0e0;flex-shrink:0">';
        h += '<h3 style="margin:0;font-size:16px">\u{1f4c4} \u7b80\u5386\u9884\u89c8</h3>';
        h += '<div>';
        h += '<button class="btn" style="margin-right:8px;font-size:13px;padding:5px 12px" onclick="toggleResumeMdEdit()">\u270f \u5feb\u901f\u7f16\u8f91</button>';
        h += '<a class="btn" style="margin-right:8px;font-size:13px;padding:5px 12px" href="/resume_view?job_id=' + jobId + '" target="_blank">\u{1f58a} \u5168\u5c4f\u7f16\u8f91</a>';
        h += '<button style="background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px;line-height:1" onclick="this.closest(\'#resume-view-modal\').remove()">\u00d7</button>';
        h += '</div></div>';
        h += '<div id="resume-view-content" style="overflow-y:auto;padding:20px;line-height:1.7;font-size:14px">';
        h += '<div style="text-align:center;padding:40px;color:#999">\u52a0\u8f7d\u4e2d...</div></div>';
        h += '<div id="md-resize-handle" style="height:6px;background:#e0e0e0;cursor:ns-resize;user-select:none;display:none;flex-shrink:0"></div>';
        h += '<div id="resume-view-footer" style="display:none;flex-shrink:0;overflow-y:auto">';
        h += '<div style="padding:10px 20px;border-top:1px solid #e0e0e0">';
        h += '<textarea id="resume-md-edit" style="width:100%;height:120px;border:1px solid #ddd;border-radius:6px;padding:8px;font-family:monospace;font-size:13px;box-sizing:border-box" placeholder="Markdown \u7f16\u8f91..."></textarea>';
        h += '<div style="text-align:right;margin-top:6px">';
        h += '<button class="btn btn-small" style="margin-right:4px" onclick="closeResumeMdEdit()">\u53d6\u6d88</button>';
        h += '<button class="btn btn-small btn-save" onclick="saveResumeMdFromModal()">\u{1f4be} \u4fdd\u5b58</button>';
        h += '</div></div></div>';
        document.body.insertAdjacentHTML('beforeend', h);

        // Lock card height with grid layout
        var card = document.getElementById('resume-view-card');
        if (card) {
            var hh = window.innerHeight * 0.85;
            card.style.height = hh + 'px';
            card.style.overflow = 'hidden';
            card.style.display = 'grid';
            // header auto, preview 1fr, handle auto, footer auto
            card.style.gridTemplateRows = 'auto 1fr auto auto';
            var preview = document.getElementById('resume-view-content');
            preview.style.overflowY = 'auto';
            preview.style.minHeight = '0';
        }

        try {
            var r = await fetch('/api/preview_resume?job_id=' + jobId);
            document.getElementById('resume-view-content').innerHTML = await r.text() || '<p style="color:#888">\u6682\u65e0\u5185\u5bb9</p>';
        } catch(e) {
            document.getElementById('resume-view-content').innerHTML = '<p style="color:red">\u52a0\u8f7d\u5931\u8d25: ' + e + '</p>';
        }
    };
})();

function toggleResumeMdEdit() {
    var f = document.getElementById('resume-view-footer');
    var h = document.getElementById('md-resize-handle');
    var p = document.getElementById('resume-view-content');
    var card = document.getElementById('resume-view-card');
    if (f.style.display === 'none' || f.style.display === '') {
        f.style.display = 'block';
        h.style.display = 'block';
        // Switch preview from 1fr to fixed px
        var header = card.querySelector(':scope > div:first-child');
        var headerH = header.offsetHeight;
        var cardH = card.clientHeight;
        var avail = cardH - headerH - 6;  // minus handle
        // Preview gets 60%, footer gets 40% of remaining
        var pH = Math.round(avail * 0.6);
        p.style.gridRow = '2';
        p.style.height = pH + 'px';
        card.style.gridTemplateRows = 'auto ' + pH + 'px auto 1fr';
        fetch('/api/get_resume_markdown', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({job_id: window._resumeJobId})})
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.success) document.getElementById('resume-md-edit').value = d.markdown || ''; });
    } else {
        f.style.display = 'none';
        h.style.display = 'none';
        card.style.gridTemplateRows = 'auto 1fr auto auto';
        p.style.height = '';
    }
}

function closeResumeMdEdit() {
    document.getElementById('resume-view-footer').style.display = 'none';
    document.getElementById('md-resize-handle').style.display = 'none';
    var card = document.getElementById('resume-view-card');
    var p = document.getElementById('resume-view-content');
    card.style.gridTemplateRows = 'auto 1fr auto auto';
    p.style.height = '';
}

async function saveResumeMdFromModal() {
    var jid = window._resumeJobId;
    var md = document.getElementById('resume-md-edit').value;
    try {
        var r = await fetch('/api/save_job_resume_md', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({job_id: jid, markdown: md})});
        var d = await r.json();
        if (d.success) {
            var r2 = await fetch('/api/preview_resume?job_id=' + jid);
            document.getElementById('resume-view-content').innerHTML = await r2.text() || '<p style="color:#888">\u6682\u65e0\u5185\u5bb9</p>';
            alert('\u2705 \u5df2\u4fdd\u5b58');
            document.getElementById('resume-view-footer').style.display = 'none';
            document.getElementById('md-resize-handle').style.display = 'none';
            var card = document.getElementById('resume-view-card');
            var p = document.getElementById('resume-view-content');
            card.style.gridTemplateRows = 'auto 1fr auto auto';
            p.style.height = '';
        } else {
            alert('\u274c \u4fdd\u5b58\u5931\u8d25: ' + (d.error || ''));
        }
    } catch(e) {
        alert('\u274c \u4fdd\u5b58\u51fa\u9519: ' + e);
    }
}

// Drag resize: change preview row height in grid
// grid: header(auto) / preview(px) / handle(auto) / footer(1fr)
document.addEventListener('mousedown', function(e) {
    var handle = e.target.closest('#md-resize-handle');
    if (!handle) return;
    e.preventDefault();
    var preview = document.getElementById('resume-view-content');
    var card = document.getElementById('resume-view-card');
    if (!preview || !card) return;
    var startY = e.clientY;
    var startH = preview.clientHeight;

    function onMove(ev) {
        var delta = ev.clientY - startY;
        var cardH = card.clientHeight;
        var header = card.querySelector(':scope > div:first-child');
        var headerH = header ? header.clientHeight : 0;
        var maxPH = cardH - headerH - 6 - 80;
        var pH = Math.max(80, Math.min(maxPH, startH + delta));
        preview.style.height = pH + 'px';
        card.style.gridTemplateRows = 'auto ' + pH + 'px auto 1fr';
    }
    function onUp() {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
});
