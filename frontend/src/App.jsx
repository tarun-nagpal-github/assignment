import React, { useState, useCallback, useEffect } from 'react'

const API = '' // use Vite proxy: /search, /tags

function useSearch() {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState({
    industry: [],
    size_range: null,
    country: null,
    locality: '',
    year_min: null,
    year_max: null,
  })
  const [countryScope, setCountryScope] = useState(null) // region selector: null = All regions
  const [page, setPage] = useState(1)
  const [size] = useState(20)
  const [sort, setSort] = useState('relevance')
  const [searchTrigger, setSearchTrigger] = useState(0) // increment to force search after Clear
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runSearch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query || null,
          filters: {
            industry: filters.industry.length ? filters.industry : null,
            size_range: filters.size_range || null,
            country: filters.country || null,
            locality: filters.locality || null,
            year_min: filters.year_min ?? null,
            year_max: filters.year_max ?? null,
          },
          country_scope: countryScope || null,
          page,
          size,
          sort,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const json = await res.json()
      setData(json)
    } catch (e) {
      setError(e.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [query, filters, countryScope, page, size, sort])

  useEffect(() => {
    runSearch()
  }, [page, sort, countryScope, searchTrigger])

  return { query, setQuery, filters, setFilters, countryScope, setCountryScope, page, setPage, size, sort, setSort, setSearchTrigger, data, loading, error, runSearch }
}

const USER_ID = 'default-user'

function App() {
  const {
    query, setQuery, filters, setFilters, countryScope, setCountryScope, page, setPage, sort, setSort, setSearchTrigger,
    data, loading, error, runSearch,
  } = useSearch()

  const [regions, setRegions] = useState([])
  const [tags, setTags] = useState([])
  const [newTagName, setNewTagName] = useState('')

  const loadRegions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/regions`)
      if (res.ok) {
        const json = await res.json()
        setRegions(json.regions || [])
      }
    } catch (_) {}
  }, [])
  useEffect(() => { loadRegions() }, [loadRegions])

  const loadTags = useCallback(async () => {
    try {
      const res = await fetch(`${API}/tags/${USER_ID}`)
      if (res.ok) {
        const json = await res.json()
        setTags(json.tags || [])
      }
    } catch (_) {}
  }, [])

  useEffect(() => { loadTags() }, [loadTags])

  const handleApplyTag = async (tag) => {
    const snap = tag.filter_snapshot || {}
    const newFilters = {
      industry: snap.industry || [],
      size_range: snap.size_range || null,
      country: snap.country || null,
      locality: snap.locality || '',
      year_min: snap.year_min ?? null,
      year_max: snap.year_max ?? null,
      country_scope: snap.country_scope ?? null,
    }
    setFilters(newFilters)
    setCountryScope(newFilters.country_scope ?? null)
    setPage(1)
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
          query,
          filters: {
            industry: newFilters.industry.length ? newFilters.industry : null,
            size_range: newFilters.size_range,
            country: newFilters.country,
            locality: newFilters.locality || null,
            year_min: newFilters.year_min,
            year_max: newFilters.year_max,
          },
          country_scope: newFilters.country_scope || null,
          page: 1,
          size: 20,
          sort,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const json = await res.json()
      setData(json)
    } catch (e) {
      setError(e.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateTag = async () => {
    const name = newTagName.trim()
    if (!name) return
    try {
      await fetch(`${API}/tags/${USER_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          filter_snapshot: {
            industry: filters.industry,
            size_range: filters.size_range,
            country: filters.country,
            locality: filters.locality,
            year_min: filters.year_min,
            year_max: filters.year_max,
            country_scope: countryScope,
          },
        }),
      })
      setNewTagName('')
      loadTags()
    } catch (_) {}
  }

  const handleDeleteTag = async (tagId) => {
    try {
      await fetch(`${API}/tags/${USER_ID}/${tagId}`, { method: 'DELETE' })
      loadTags()
    } catch (_) {}
  }

  const facets = data?.facets || {}
  const hits = data?.hits || []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / 20) || 1

  const toggleIndustry = (val) => {
    setFilters((f) => ({
      ...f,
      industry: f.industry.includes(val) ? f.industry.filter((x) => x !== val) : [...f.industry, val],
    }))
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">CompanySearch</h1>
      </header>
      <div className="app-body">
      <aside className="sidebar">
        <input
          type="search"
          className="search-box"
          placeholder="Search companies..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runSearch()}
        />
        <button type="button" className="btn btn-primary btn-block" onClick={runSearch}>
          Search
        </button>
        <button
          type="button"
          className="btn btn-block"
          onClick={() => {
            setQuery('')
            setFilters({
              industry: [], size_range: null, country: null, locality: '',
              year_min: null, year_max: null,
            })
            setCountryScope(null)
            setPage(1)
            setSearchTrigger((t) => t + 1)
          }}
        >
          Clear
        </button>

        <div className="filter-section region-selector">
          <label htmlFor="region-select">Region</label>
          <select
            id="region-select"
            value={countryScope ?? ''}
            onChange={(e) => {
              const v = e.target.value
              setCountryScope(v === '' ? null : v)
              setPage(1)
            }}
          >
            <option value="">All regions</option>
            {regions.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </div>

        <details className="filter-section" open>
          <summary>Industry</summary>
          <ul>
            {(facets.industry || []).map((b) => (
              <li key={b.value} onClick={() => toggleIndustry(b.value)}>
                <input
                  type="checkbox"
                  checked={filters.industry.includes(b.value)}
                  onChange={() => {}}
                />
                <span>{b.value}</span>
                <span className="count">{b.count}</span>
              </li>
            ))}
          </ul>
        </details>
        <details className="filter-section">
          <summary>Size range</summary>
          <ul>
            {(facets.size_range || []).map((b) => (
              <li
                key={b.value}
                onClick={() => {
                  setFilters((f) => ({ ...f, size_range: f.size_range === b.value ? null : b.value }))
                  setPage(1)
                }}
              >
                <input type="radio" checked={filters.size_range === b.value} onChange={() => {}} />
                <span>{b.value}</span>
                <span className="count">{b.count}</span>
              </li>
            ))}
          </ul>
        </details>
        <details className="filter-section">
          <summary>Country</summary>
          <ul>
            {(facets.country || []).map((b) => (
              <li
                key={b.value}
                onClick={() => {
                  setFilters((f) => ({ ...f, country: f.country === b.value ? null : b.value }))
                  setPage(1)
                }}
              >
                <input type="radio" checked={filters.country === b.value} onChange={() => {}} />
                <span>{b.value}</span>
                <span className="count">{b.count}</span>
              </li>
            ))}
          </ul>
        </details>
        <details className="filter-section">
          <summary>Year founded</summary>
          <div className="input-row">
            <input
              type="number"
              placeholder="Min"
              value={filters.year_min ?? ''}
              onChange={(e) =>
                setFilters((f) => ({ ...f, year_min: e.target.value === '' ? null : parseInt(e.target.value, 10) }))
              }
            />
            <input
              type="number"
              placeholder="Max"
              value={filters.year_max ?? ''}
              onChange={(e) =>
                setFilters((f) => ({ ...f, year_max: e.target.value === '' ? null : parseInt(e.target.value, 10) }))
              }
            />
          </div>
        </details>

        <div className="tags-section">
          <h4>My tags</h4>
          <ul className="tags-list">
            {tags.map((t) => (
              <li key={t.id}>
                <span>{t.name}</span>
                <span>
                  <button type="button" className="apply" onClick={() => handleApplyTag(t)}>Apply</button>
                  <button type="button" onClick={() => handleDeleteTag(t.id)}>Delete</button>
                </span>
              </li>
            ))}
          </ul>
          <div className="tag-create">
            <input
              placeholder="New tag name"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateTag()}
            />
            <button type="button" className="btn btn-primary" onClick={handleCreateTag}>Save</button>
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="results-header">
          <span className="total">{total.toLocaleString()} companies</span>
          <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1) }}>
            <option value="relevance">Relevance</option>
            <option value="name_asc">Name A–Z</option>
            <option value="name_desc">Name Z–A</option>
            <option value="size_desc">Largest first</option>
            <option value="size_asc">Smallest first</option>
            <option value="year_desc">Newest first</option>
            <option value="year_asc">Oldest first</option>
          </select>
        </div>

        {loading && <div className="loading">Loading…</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && (
          <>
            <div className="results-list">
              {hits.map((company) => (
                <article key={company.id} className="card">
                  <h3>
                    <a href={company.domain ? `https://${company.domain}` : '#'} target="_blank" rel="noopener noreferrer">
                      {company.name}
                    </a>
                  </h3>
                  <div className="meta">
                    {company.industry && <span>{company.industry}</span>}
                    {company.country && <span>{company.locality ? `${company.locality}, ${company.country}` : company.country}</span>}
                    {company.year_founded != null && <span>Founded {company.year_founded}</span>}
                    {company.size_range && <span>Size: {company.size_range}</span>}
                    {(company.current_employee_estimate != null || company.total_employee_estimate != null) && (
                      <span>Employees: {company.current_employee_estimate ?? company.total_employee_estimate ?? '—'}</span>
                    )}
                  </div>
                </article>
              ))}
            </div>
            <div className="pagination">
              <button type="button" className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button type="button" className="btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next
              </button>
            </div>
          </>
        )}
      </main>
      </div>
    </div>
  )
}

export default App
