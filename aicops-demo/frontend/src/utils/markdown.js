import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,       // 禁止原始 HTML 标签，防止 XSS
  linkify: true,
  typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch (_) {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

export function renderMarkdown(content) {
  if (!content) return ''
  // html: false 已确保 <script> 等标签被转义；此处额外过滤 javascript: 协议链接
  const rendered = md.render(content)
  return rendered.replace(/href\s*=\s*["']javascript:[^"']*["']/gi, 'href="#"')
}
