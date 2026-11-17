import { useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'

let plotlyPromise
const loadPlotly = () => (plotlyPromise ||= import('plotly.js-dist-min').then((m) => m.default || m))

export const CHART_COLORS = ['#b4532a', '#111111', '#8a8378', '#c9a27e', '#3f5a6b', '#6d2233', '#6b6b47', '#d8c3a5']
export const CHART_COLORS_DARK = ['#e07a4f', '#f2efe8', '#9b978e', '#c9a27e', '#7fa3b8', '#c45a6e', '#a3a36b', '#d8c3a5']

/** Plotly 래퍼: 코드 스플리팅 + 다크모드 대응 + 반응형 리사이즈 */
export default function Plot({ data, layout = {}, height = 320, className = '' }) {
  const ref = useRef(null)
  const { dark } = useTheme()

  useEffect(() => {
    let alive = true
    const el = ref.current
    loadPlotly().then((Plotly) => {
      if (!alive || !el) return
      const fg = dark ? '#f2efe8' : '#111111'
      const grid = dark ? '#2b2b2b' : '#e8e4dc'
      Plotly.react(
        el,
        data,
        {
          height,
          margin: { l: 40, r: 16, t: 16, b: 40 },
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { family: 'Pretendard Variable, Pretendard, sans-serif', color: fg, size: 12 },
          colorway: dark ? CHART_COLORS_DARK : CHART_COLORS,
          xaxis: { gridcolor: grid, zerolinecolor: grid, ...layout.xaxis },
          yaxis: { gridcolor: grid, zerolinecolor: grid, ...layout.yaxis },
          legend: { orientation: 'h', y: -0.2, ...layout.legend },
          ...Object.fromEntries(Object.entries(layout).filter(([k]) => !['xaxis', 'yaxis', 'legend'].includes(k))),
        },
        { responsive: true, displayModeBar: false },
      )
    })
    return () => {
      alive = false
    }
  }, [data, layout, height, dark])

  useEffect(() => {
    const el = ref.current
    return () => loadPlotly().then((Plotly) => el && Plotly.purge(el))
  }, [])

  return <div ref={ref} className={`w-full ${className}`} style={{ minHeight: height }} />
}
