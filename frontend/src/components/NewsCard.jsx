import React from 'react'
import { ExternalLink } from 'lucide-react'

// Strip HTML tags from text
const stripHtml = (html) => {
  if (!html) return '';
  const text = html.replace(/<[^>]*>/g, '');
  const txt = document.createElement('textarea');
  txt.innerHTML = text;
  return txt.value;
}

export default function NewsCard({ article }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl border border-white/5 bg-dark/40 p-4 transition-all hover:border-blue-500/50 hover:bg-dark/60"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="text-sm font-bold text-primary group-hover:text-blue-400 mb-2 leading-snug">
            {article.title}
          </h3>

          {/* Content Description */}
          {article.content && (
            <p className="text-xs text-gray-400 mb-3 line-clamp-2 leading-relaxed">
              {stripHtml(article.content)}
            </p>
          )}

          {/* Source and Affected Companies */}
          <div className="flex items-center gap-2 flex-wrap">
            {article.source && (
              <span className="text-[10px] text-gray-500 font-medium">
                {article.source}
              </span>
            )}
            {(article.affected_companies || article.companies_mentioned || []).map((company, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 rounded-full bg-red-500/20 px-2.5 py-1 text-[10px] font-black text-red-300 uppercase tracking-wider border border-red-500/30"
              >
                ⚠ {company}
              </span>
            ))}
          </div>
        </div>
        <ExternalLink size={16} className="text-gray-600 group-hover:text-blue-400 transition-colors flex-shrink-0" />
      </div>
    </a>
  )
}
