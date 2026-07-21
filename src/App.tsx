import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type SortKey = 'calories' | 'protein' | 'sugar'
type Food = {
  id: number; food_code: string; name: string; manufacturer: string
  category_large: string; category_medium: string; original_basis: string
  calories: number | null; protein: number | null; sugar: number | null
}
type Meta = { total: number; categories: string[]; mediumCategories: string[] }

const sortInfo: Record<SortKey, { label: string; icon: string; description: string }> = {
  calories: { label: '저칼로리', icon: '◔', description: '칼로리 낮은 순' },
  protein: { label: '고단백', icon: '◇', description: '단백질 높은 순' },
  sugar: { label: '저당류', icon: '◡', description: '당류 낮은 순' },
}

const API_BASE = 'http://127.0.0.1:8787'

const fmt = (value: number | null, unit: string) => value == null ? '—' : `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}${unit}`

export default function App() {
  const [dataType, setDataType] = useState('가공식품')
  const [sort, setSort] = useState<SortKey>('calories')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [medium, setMedium] = useState('')
  const [page, setPage] = useState(1)
  const [meta, setMeta] = useState<Meta>({ total: 0, categories: [], mediumCategories: [] })
  const [items, setItems] = useState<Food[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Food[]>([])
  const [filters, setFilters] = useState({ maxCalories: '', minProtein: '', maxSugar: '' })

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        const params = new URLSearchParams({ data_type: dataType, category_large: category })
        const response = await fetch(`${API_BASE}/api/meta?${params}`)
        if (!response.ok) throw new Error(await response.text())
        setMeta(await response.json())
      } catch { setError('데이터 API에 연결할 수 없습니다. start.sh로 앱을 실행해 주세요.') }
    }, 100)
    return () => clearTimeout(timer)
  }, [dataType, category])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setLoading(true); setError('')
      const params = new URLSearchParams({
        data_type: dataType, sort, q: query, category_large: category,
        category_medium: medium, page: String(page), page_size: '20',
      })
      if (filters.maxCalories) params.set('max_calories', filters.maxCalories)
      if (filters.minProtein) params.set('min_protein', filters.minProtein)
      if (filters.maxSugar) params.set('max_sugar', filters.maxSugar)
      try {
        const response = await fetch(`${API_BASE}/api/foods?${params}`, { signal: controller.signal })
        if (!response.ok) throw new Error(await response.text())
        const data = await response.json()
        setItems(data.items); setTotal(data.total)
      } catch (reason) {
        if ((reason as Error).name !== 'AbortError') setError('데이터를 불러오지 못했습니다. 서버 실행 상태를 확인해 주세요.')
      } finally { setLoading(false) }
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [dataType, sort, query, category, medium, page, filters])

  useEffect(() => { setPage(1); setMedium('') }, [dataType, category])
  const pages = Math.max(1, Math.ceil(total / 20))
  const chartData = useMemo(() => selected.map(food => ({
    name: food.name.length > 11 ? food.name.slice(0, 11) + '…' : food.name,
    칼로리: food.calories, 단백질: food.protein, 당류: food.sugar,
  })), [selected])

  function toggle(food: Food) {
    setSelected(current => current.some(item => item.id === food.id)
      ? current.filter(item => item.id !== food.id)
      : current.length < 4 ? [...current, food] : current)
  }

  function reset() {
    setQuery(''); setCategory(''); setMedium(''); setFilters({ maxCalories: '', minProtein: '', maxSugar: '' }); setPage(1)
  }

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#top">EAT-P<span>I</span>CK<i>●</i></a>
      <div className="top-copy"><strong>영양성분을 한눈에, 더 나은 선택을 간단하게</strong><small>공공데이터 기반 음식·가공식품 영양 랭킹</small></div>
      <div className="basis-badge"><b>100g</b><span>동일 기준 비교</span></div>
    </header>

    <main id="top">
      <section className="hero">
        <div><p className="eyebrow">NUTRITION RANKING</p><h1>내 기준에 맞는<br/><em>영양 랭킹</em>을 찾아보세요</h1><p>칼로리, 단백질, 당류만으로 간결하고 정확하게 비교합니다.</p></div>
        <div className="hero-stats">
          <div><b>{meta.total.toLocaleString()}</b><span>비교 가능 식품</span></div>
          <div><b>3</b><span>핵심 영양지표</span></div>
          <div><b>100g</b><span>통일된 기준</span></div>
        </div>
      </section>

      <section className="control-card">
        <div className="type-switch">
          {['가공식품', '음식'].map(type => <button className={dataType === type ? 'active' : ''} onClick={() => setDataType(type)} key={type}>{type === '가공식품' ? '▣' : '♨'} {type}</button>)}
        </div>
        <div className="ranking-tabs">
          {(Object.keys(sortInfo) as SortKey[]).map(key => <button key={key} className={sort === key ? 'active' : ''} onClick={() => { setSort(key); setPage(1) }}>
            <span>{sortInfo[key].icon}</span><b>{sortInfo[key].label}</b><small>{sortInfo[key].description}</small>
          </button>)}
        </div>
        <div className="filters">
          <label className="search"><span>⌕</span><input value={query} onChange={e => { setQuery(e.target.value); setPage(1) }} placeholder="식품명을 검색해 보세요" /></label>
          <select value={category} onChange={e => setCategory(e.target.value)}><option value="">전체 대분류</option>{meta.categories.map(value => <option key={value}>{value}</option>)}</select>
          <select value={medium} onChange={e => { setMedium(e.target.value); setPage(1) }}><option value="">전체 중분류</option>{meta.mediumCategories.map(value => <option key={value}>{value}</option>)}</select>
          <input type="number" min="0" placeholder="최대 kcal" value={filters.maxCalories} onChange={e => { setFilters({...filters, maxCalories:e.target.value}); setPage(1) }} />
          <input type="number" min="0" placeholder="최소 단백질(g)" value={filters.minProtein} onChange={e => { setFilters({...filters, minProtein:e.target.value}); setPage(1) }} />
          <input type="number" min="0" placeholder="최대 당류(g)" value={filters.maxSugar} onChange={e => { setFilters({...filters, maxSugar:e.target.value}); setPage(1) }} />
          <button className="reset" onClick={reset}>↻ 초기화</button>
        </div>
      </section>

      <section className="ranking-card">
        <div className="section-title"><div><p>100g STANDARD</p><h2>{sortInfo[sort].label} 식품 랭킹</h2><span>조건에 맞는 식품 <b>{total.toLocaleString()}개</b></span></div><div className="legend"><i className="cal"></i>칼로리 <i className="pro"></i>단백질 <i className="sug"></i>당류</div></div>
        {error && <div className="notice error">{error}</div>}
        <div className="table-wrap">
          <table>
            <thead><tr><th>순위</th><th>식품 정보</th><th>분류</th><th>칼로리</th><th>단백질</th><th>당류</th><th>비교</th></tr></thead>
            <tbody className={loading ? 'loading' : ''}>
              {!loading && items.map((food, index) => <tr key={food.id}>
                <td><strong className={`rank ${page === 1 && index < 3 ? 'top' : ''}`}>{(page - 1) * 20 + index + 1}</strong></td>
                <td><div className="food-name"><span>{food.name.slice(0, 1)}</span><div><b>{food.name}</b><small>{food.manufacturer || '업체 정보 없음'} · 원본 {food.original_basis}</small></div></div></td>
                <td><small className="category">{food.category_large}<br/>{food.category_medium}</small></td>
                <td><span className="nutrient calories"><b>{fmt(food.calories, '')}</b><small>kcal</small></span></td>
                <td><span className="nutrient protein"><b>{fmt(food.protein, '')}</b><small>g</small></span></td>
                <td><span className="nutrient sugar"><b>{fmt(food.sugar, '')}</b><small>g</small></span></td>
                <td><button aria-label="비교 선택" className={`check ${selected.some(item => item.id === food.id) ? 'active' : ''}`} onClick={() => toggle(food)}>✓</button></td>
              </tr>)}
              {loading && [...Array(8)].map((_, i) => <tr key={i} className="skeleton"><td colSpan={7}><span></span></td></tr>)}
              {!loading && !items.length && !error && <tr><td colSpan={7}><div className="notice">조건에 맞는 식품이 없습니다.</div></td></tr>}
            </tbody>
          </table>
        </div>
        <div className="pagination"><button disabled={page === 1} onClick={() => setPage(page - 1)}>← 이전</button><span><b>{page}</b> / {pages.toLocaleString()}</span><button disabled={page >= pages} onClick={() => setPage(page + 1)}>다음 →</button></div>
      </section>

      <section className="compare-card">
        <div className="section-title"><div><p>COMPARE</p><h2>선택 식품 비교</h2><span>순위표에서 최대 4개를 선택하세요.</span></div><b className="selection-count">{selected.length} / 4</b></div>
        {selected.length ? <>
          <div className="selected-chips">{selected.map(food => <button key={food.id} onClick={() => toggle(food)}>{food.name}<span>×</span></button>)}</div>
          <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 5, left: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="name" tick={{fontSize:12}}/><YAxis yAxisId="left" tick={{fontSize:11}}/><YAxis yAxisId="right" orientation="right" tick={{fontSize:11}}/><Tooltip/><Legend/><Bar yAxisId="left" dataKey="칼로리" fill="#ffad2f" radius={[5,5,0,0]}/><Bar yAxisId="right" dataKey="단백질" fill="#16784d" radius={[5,5,0,0]}/><Bar yAxisId="right" dataKey="당류" fill="#67a8dc" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>
        </> : <div className="empty-compare"><span>＋</span><b>비교할 식품을 선택해 주세요</b><small>랭킹 오른쪽 체크 버튼을 누르면 여기에 차트가 표시됩니다.</small></div>}
      </section>
    </main>
    <footer><b>EAT-PICK</b><span>식품의약품안전처 공공데이터를 가공한 참고용 정보입니다.</span></footer>
  </div>
}
