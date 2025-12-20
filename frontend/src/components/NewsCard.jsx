import React from 'react'
import { ExternalLink, Calendar, Building2 } from 'lucide-react'

export default function NewsCard({ article }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-lg border border-gray-700 bg-gradient-to-r from-gray-800 to-gray-900 p-4 transition-all hover:border-blue-500 hover:shadow-lg hover:shadow-blue-500/20"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-white group-hover:text-blue-400 mb-2">
            {article.title}
          </h3>
          {article.content && (
            <p className="mt-2 text-sm text-gray-400 line-clamp-2">
              {article.content}
            </p>
          )}
          <div className="mt-3 flex items-center gap-3 flex-wrap">
            <span className="text-xs font-medium text-gray-500 flex items-center gap-1">
              <Building2 size={12} />
              {article.source}
            </span>
            <span className="text-xs text-gray-600 flex items-center gap-1">
              <Calendar size={12} />
              {new Date(article.published_at || article.publishedAt).toLocaleDateString()}
            </span>
            {article.companies_mentioned && article.companies_mentioned.length > 0 && (
              <>
                {article.companies_mentioned.map((company, idx) => (
                  <span
                    key={idx}
                    className="inline-block rounded-full bg-blue-500/20 px-2 py-1 text-xs font-medium text-blue-300"
                  >
                    {company}
                  </span>
                ))}
              </>
            )}
          </div>
        </div>
        <div className="ml-4 text-2xl opacity-0 group-hover:opacity-100 transition-opacity">
          🔗
        </div>
      </div>
    </a>
  )
}
