#!/usr/bin/env python3
"""Inject handle_resume_page into job_agent_web.py"""

import textwrap

with open("job_agent_web.py", "r") as f:
    content = f.read()

marker = '    # ===================== 工具 ====================='
insert = textwrap.dedent("""\
    # ===================== 页面 =====================

    def handle_resume_page(self, params):
        lang = self._get_lang(params)
        title = t(lang, 'resume_title')
        upload_text = t(lang, 'resume_upload')
        upload_hint = t(lang, 'resume_upload_hint')
        empty_text = t(lang, 'resume_empty')
        delete_text = t(lang, 'resume_delete')
        html = self._page(title, \"\"\"
        <h1>RESUME_TITLE</h1>
        <div id=\"resume-list\"></div>
        <div style=\"margin-top:16px\">
            <button onclick=\"uploadResume()\" class=\"btn btn-primary\">UPLOAD_TEXT</button>
            <span style=\"margin-left:8px;color:#888;font-size:12px\">UPLOAD_HINT</span>
        </div>
        <script>
        async function loadResumes() {
            var resp = await (await fetch('/api/list_resumes')).json();
            var list = document.getElementById('resume-list');
            if (!resp.success || resp.resumes.length === 0) {
                list.innerHTML = '<p style=\"margin-top:16px;color:#888\">EMPTY_TEXT</p>';
                return;
            }
            var h = '';
            resp.resumes.forEach(function(r) {
                h += '<div style=\"display:flex;align-items:center;justify-content:space-between;padding:12px;border:1px solid #e0e0e0;border-radius:8px;margin-top:8px\">';
                h += '<div><span style=\"font-weight:bold\">\\u{1F4C4} ' + r.name + '</span><br><span style=\"font-size:12px;color:#888\">' + r.created_at + '</span></div>';
                h += '<div>';
                h += '<a href=\"/api/get_resume?resume_id=' + r.id + '\" target=\"_blank\" class=\"btn btn-small\">\\u{1F441}\\u200D\\u{1F5E8}\\uFE0F PREVIEW_TEXT</a>';
                h += '<button onclick=\"delResume(\\'' + r.id + '\\')\" class=\"btn btn-small btn-delete\" style=\"margin-left:6px\">DELETE_TEXT</button>';
                h += '</div></div>';
            });
            list.innerHTML = h;
        }
        async function delResume(id) {
            if (!confirm('确定删除？')) return;
            await fetch('/api/delete_resume', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({resume_id:id})});
            loadResumes();
        }
        async function uploadResume() {
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = '.pdf,.doc,.docx';
            input.onchange = async function(e) {
                var file = e.target.files[0];
                if (!file) return;
                var reader = new FileReader();
                reader.onload = async function(ev) {
                    var b64 = ev.target.result.split(',')[1];
                    var name = file.name || '未命名简历';
                    var resp = await fetch('/api/add_resume', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, file:b64})});
                    var d = await resp.json();
                    if (d.success) {
                        loadResumes();
                    } else {
                        alert('上传失败: ' + (d.error || ''));
                    }
                };
                reader.readAsDataURL(file);
            };
            input.click();
        }
        loadResumes();
        </script>
        \"\"\".replace('RESUME_TITLE',title).replace('UPLOAD_TEXT',upload_text).replace('UPLOAD_HINT',upload_hint).replace('EMPTY_TEXT',empty_text).replace('DELETE_TEXT',delete_text).replace('PREVIEW_TEXT','预览'), lang=lang)
        self._send_html(html)

    """ + marker)


content = content.replace(marker, insert, 1)

with open("job_agent_web.py", "w") as f:
    f.write(content)

print("Done")
