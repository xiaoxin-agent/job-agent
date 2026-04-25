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
        h += '<div style="background:#fff;border-radius:12px;padding:0;max-width:700px;width:95%;max-height:85vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.2)">';
        h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid #e0e0e0;flex-shrink:0">';
        h += '<h3 style="margin:0;font-size:16px">\u{1f4c4} \u7b80\u5386\u9884\u89c8</h3>';
        h += '<div>';
        h += '<button class="btn" style="margin-right:8px;font-size:13px;padding:5px 12px" onclick="toggleResumeMdEdit()">\u270f \u5feb\u901f\u7f16\u8f91</button>';
        h += '<a class="btn" style="margin-right:8px;font-size:13px;padding:5px 12px" href="/resume_view?job_id=' + jobId + '" target="_blank">\u{1f58a} \u5168\u5c4f\u7f16\u8f91</a>';
        h += '<button style="background:none;border:none;font-size:20px;cursor:pointer;color:#888;padding:4px;line-height:1" onclick="this.closest(\'#resume-view-modal\').remove()">\u00d7</button>';
        h += '</div></div>';
        h += '<div id="resume-view-content" style="flex:1;overflow-y:auto;padding:20px;line-height:1.7;font-size:14px">';
        h += '<div style="text-align:center;padding:40px;color:#999">\u52a0\u8f7d\u4e2d...</div></div>';
        h += '<div id="resume-view-footer" style="border-top:1px solid #e0e0e0;display:none;flex-shrink:0;position:relative">';
        h += '<div style="padding:10px 20px">';
        h += '<textarea id="resume-md-edit" style="width:100%;height:120px;border:1px solid #ddd;border-radius:6px;padding:8px;font-family:monospace;font-size:13px;box-sizing:border-box" placeholder="Markdown \u7f16\u8f91..."></textarea>';
        h += '<div id="md-resize-handle" style="height:6px;background:#e0e0e0;cursor:ns-resize;user-select:none;margin:6px 0"></div>';
        h += '<div style="text-align:right">';
        h += '<button class="btn btn-small" style="margin-right:4px" onclick="closeResumeMdEdit()">\u53d6\u6d88</button>';
        h += '<button class="btn btn-small btn-save" onclick="saveResumeMdFromModal()">\u{1f4be} \u4fdd\u5b58</button>';
        h += '</div></div></div>';
        h += '</div></div>';
        document.body.insertAdjacentHTML('beforeend', h);

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
    if (f.style.display === 'none' || f.style.display === '') {
        f.style.display = 'block';
        fetch('/api/get_resume_markdown', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({job_id: window._resumeJobId})})
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.success) document.getElementById('resume-md-edit').value = d.markdown || ''; });
    } else {
        f.style.display = 'none';
    }
}

function closeResumeMdEdit() {
    document.getElementById('resume-view-footer').style.display = 'none';
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
        } else {
            alert('\u274c \u4fdd\u5b58\u5931\u8d25: ' + (d.error || ''));
        }
    } catch(e) {
        alert('\u274c \u4fdd\u5b58\u51fa\u9519: ' + e);
    }
}

// MD editor resize handle
document.addEventListener('mousedown', function(e) {
    var handle = e.target.closest('#md-resize-handle');
    if (!handle) return;
    e.preventDefault();
    var footer = document.getElementById('resume-view-footer');
    var textarea = document.getElementById('resume-md-edit');
    var startY = e.clientY;
    var startH = textarea.clientHeight;

    function onMove(ev) {
        var h = Math.max(60, startH + (ev.clientY - startY));
        textarea.style.height = h + 'px';
        textarea.style.resize = 'none';
    }
    function onUp() {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        textarea.style.resize = 'vertical';
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
});
