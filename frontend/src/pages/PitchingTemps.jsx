import useRoster from '../hooks/useRoster'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ScatterChart, Scatter, ResponsiveContainer, ReferenceLine, Cell,
  LineChart, Line,
} from 'recharts'
import styles from './PitchingTemps.module.css'

const PRIMARY   = '#0C2C56'
const SECONDARY = '#005C5C'
const ACCENT    = '#C4CED4'

const PITCHER_COLORS = [
  '#4FC3F7', '#81C784', '#FFB74D', '#F06292',
  '#BA68C8', '#4DB6AC', '#FF8A65', '#A1887F',
]

const ERA_GOOD  = '#4CAF50'
const ERA_BAD   = '#e05252'
const ERA_MID   = '#FFB74D'

const TEMP_COLORS = ['#64B5F6', '#81C784', '#FFB74D', '#EF5350']

export default function PitchingTemps() {
  const { data, loading, error } = useRoster('/api/mariners/pitching-temps/')

  if (loading) return (
    <LoadingSpinner
      color="#005C5C"
      message="Fetching 162 games from MLB API — first load takes ~35 seconds…"
    />
  )
  if (error) return <div className={styles.error}>Failed to load analysis: {error}</div>

  const { meta, correlation, temp_buckets, per_pitcher, env_comparison, scatter } = data

  const bucketChartData = temp_buckets
    .filter(b => !b.insufficient)
    .map((b, i) => ({ ...b, color: TEMP_COLORS[i] }))

  const envChartData = [
    { name: 'Outdoor', era: env_comparison.outdoor.era, whip: env_comparison.outdoor.whip, k9: env_comparison.outdoor.k9 },
    { name: 'Roof Closed', era: env_comparison.controlled.era, whip: env_comparison.controlled.whip, k9: env_comparison.controlled.k9 },
  ]

  // Build pitcher color map for scatter
  const pitcherNames = [...new Set(scatter.map(s => s.pitcher))]
  const colorMap = Object.fromEntries(
    pitcherNames.map((name, i) => [name, PITCHER_COLORS[i % PITCHER_COLORS.length]])
  )

  // Custom scatter tooltip
  const ScatterTip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className={styles.tooltip}>
        <div className={styles.ttPitcher}>{d.pitcher}</div>
        <div>{d.date} · {d.opponent}</div>
        <div>{d.temp_f}°F · ERA {d.era?.toFixed(2)} · {d.ip_dec?.toFixed(1)} IP</div>
      </div>
    )
  }

  const BarTip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className={styles.tooltip}>
        <div className={styles.ttLabel}>{label}</div>
        {payload.map(p => (
          <div key={p.name} style={{ color: p.color }}>{p.name}: {p.value?.toFixed(2)}</div>
        ))}
      </div>
    )
  }

  return (
    <div className={styles.page}>

      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.eyebrow}>MLB · Analytics</div>
        <h1 className={styles.title}>Mariners Starting Pitching by Temperature</h1>
        <p className={styles.sub}>
          How game-day temperature affects rotation performance · 2025 regular season
        </p>
      </div>

      {/* ── Key findings ── */}
      <div className={styles.findings}>
        <FindingCard
          label="Pearson r (Temp vs ERA)"
          value={correlation?.r?.toFixed(3) ?? '—'}
          sub={correlation?.significant
            ? `p = ${correlation.p_value.toFixed(4)} · Statistically significant`
            : `p = ${correlation?.p_value?.toFixed(4)} · Not significant`}
          highlight={correlation?.significant ? 'sig' : 'neutral'}
        />
        <FindingCard
          label="Best Temp Range (ERA)"
          value={bucketChartData.reduce((best, b) => b.era < (best?.era ?? Infinity) ? b : best, null)?.label ?? '—'}
          sub={`ERA ${bucketChartData.reduce((best, b) => b.era < (best?.era ?? Infinity) ? b : best, null)?.era?.toFixed(2) ?? '—'}`}
          highlight="good"
        />
        <FindingCard
          label="Worst Temp Range (ERA)"
          value={bucketChartData.reduce((worst, b) => b.era > (worst?.era ?? -Infinity) ? b : worst, null)?.label ?? '—'}
          sub={`ERA ${bucketChartData.reduce((worst, b) => b.era > (worst?.era ?? -Infinity) ? b : worst, null)?.era?.toFixed(2) ?? '—'}`}
          highlight="bad"
        />
        <FindingCard
          label="Outdoor vs Roof Closed"
          value={`${env_comparison.outdoor.era} vs ${env_comparison.controlled.era}`}
          sub={`ERA outdoor vs controlled · ${meta.outdoor_starts} outdoor, ${meta.controlled_starts} controlled`}
          highlight="neutral"
        />
      </div>

      {/* ── Scatter: temp vs per-start ERA ── */}
      <Section
        title="Temperature vs Per-Start ERA"
        subtitle={`${meta.outdoor_starts} outdoor starts · each point = one outing · colored by pitcher`}
      >
        <ResponsiveContainer width="100%" height={350}>
          <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis
              dataKey="temp_f"
              type="number"
              name="Temperature"
              label={{ value: 'Game Temperature (°F)', position: 'insideBottom', offset: -10, fill: '#5a7a90', fontSize: 12 }}
              tick={{ fill: '#a0adb8', fontSize: 12 }}
              domain={['dataMin - 3', 'dataMax + 3']}
            />
            <YAxis
              dataKey="era"
              type="number"
              name="ERA"
              label={{ value: 'ERA', angle: -90, position: 'insideLeft', fill: '#5a7a90', fontSize: 12 }}
              tick={{ fill: '#a0adb8', fontSize: 12 }}
              domain={[0, 'dataMax + 1']}
            />
            <Tooltip content={<ScatterTip />} />
            {pitcherNames.map(name => (
              <Scatter
                key={name}
                name={name.split(' ').slice(-1)[0]}
                data={scatter.filter(s => s.pitcher === name && s.era !== null)}
                fill={colorMap[name]}
                opacity={0.75}
              />
            ))}
            <Legend
              wrapperStyle={{ color: '#a0adb8', fontSize: 12, paddingTop: 8 }}
              formatter={(value) => value}
            />
          </ScatterChart>
        </ResponsiveContainer>
        {correlation && (
          <p className={styles.chartNote}>
            Pearson r = {correlation.r} (n = {correlation.n}) · {correlation.interpretation}
          </p>
        )}
      </Section>

      {/* ── ERA by temperature bucket ── */}
      <Section
        title="ERA by Temperature Range"
        subtitle="Aggregate ERA across all rotation starts in each temperature band (outdoor only)"
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={bucketChartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="label" tick={{ fill: '#a0adb8', fontSize: 13 }} />
            <YAxis tick={{ fill: '#a0adb8', fontSize: 12 }} domain={[0, 7]} tickFormatter={v => v.toFixed(1)} />
            <Tooltip content={<BarTip />} />
            <Bar dataKey="era" name="ERA" radius={[5, 5, 0, 0]}>
              {bucketChartData.map((entry, i) => (
                <Cell key={i} fill={TEMP_COLORS[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className={styles.bucketTable}>
          <table>
            <thead>
              <tr>
                <th>Temp Range</th><th>Starts</th><th>ERA</th><th>WHIP</th><th>K/9</th><th>Avg IP</th>
              </tr>
            </thead>
            <tbody>
              {temp_buckets.map(b => (
                <tr key={b.label}>
                  <td>{b.label}</td>
                  <td>{b.starts}</td>
                  <td className={b.era < 3.7 ? styles.good : b.era > 4.5 ? styles.bad : ''}>{b.insufficient ? '—' : b.era?.toFixed(2)}</td>
                  <td>{b.insufficient ? '—' : b.whip?.toFixed(3)}</td>
                  <td>{b.insufficient ? '—' : b.k9?.toFixed(2)}</td>
                  <td>{b.insufficient ? '—' : b.avg_ip?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {/* ── Outdoor vs Controlled ── */}
      <Section
        title="Outdoor vs. Controlled Environment"
        subtitle="T-Mobile Park's retractable roof creates two distinct pitching contexts"
      >
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={envChartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="name" tick={{ fill: '#a0adb8', fontSize: 13 }} />
            <YAxis tick={{ fill: '#a0adb8', fontSize: 12 }} />
            <Tooltip content={<BarTip />} />
            <Legend wrapperStyle={{ color: '#a0adb8' }} />
            <Bar dataKey="era"  name="ERA"  fill="#EF5350" radius={[5,5,0,0]} />
            <Bar dataKey="whip" name="WHIP" fill="#FFB74D" radius={[5,5,0,0]} />
            <Bar dataKey="k9"   name="K/9"  fill="#4FC3F7" radius={[5,5,0,0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className={styles.chartNote}>
          {meta.controlled_starts} starts with roof closed (ERA {env_comparison.controlled.era}) vs {meta.outdoor_starts} outdoor starts (ERA {env_comparison.outdoor.era}).
          {env_comparison.controlled.era < env_comparison.outdoor.era
            ? ' The rotation performs better in the controlled T-Mobile environment — likely reflecting both favorable pitching conditions and selection bias (roof closed on cold/wet days).'
            : ' No meaningful difference between environments.'}
        </p>
      </Section>

      {/* ── Per pitcher breakdown ── */}
      <Section
        title="Per-Pitcher Temperature Splits"
        subtitle="Cold = < 60°F outdoor starts · Warm = ≥ 70°F outdoor starts (min 3 starts to show)"
      >
        <div className={styles.pitcherTable}>
          <table>
            <thead>
              <tr>
                <th>Pitcher</th>
                <th>Starts</th>
                <th>Overall ERA</th>
                <th>Overall WHIP</th>
                <th>K/9</th>
                <th>Cold ERA (n)</th>
                <th>Warm ERA (n)</th>
                <th>Diff</th>
              </tr>
            </thead>
            <tbody>
              {per_pitcher.map(p => {
                const diff = p.warm_era != null && p.cold_era != null
                  ? (p.warm_era - p.cold_era).toFixed(2)
                  : null
                return (
                  <tr key={p.name}>
                    <td className={styles.pitcherName}>{p.name}</td>
                    <td>{p.total_starts}</td>
                    <td>{p.overall_era?.toFixed(2) ?? '—'}</td>
                    <td>{p.overall_whip?.toFixed(3) ?? '—'}</td>
                    <td>{p.overall_k9?.toFixed(2) ?? '—'}</td>
                    <td className={styles.coldCell}>
                      {p.cold_era != null ? `${p.cold_era.toFixed(2)} (${p.cold_n})` : `— (${p.cold_n})`}
                    </td>
                    <td className={styles.warmCell}>
                      {p.warm_era != null ? `${p.warm_era.toFixed(2)} (${p.warm_n})` : `— (${p.warm_n})`}
                    </td>
                    <td className={diff > 0 ? styles.bad : diff < 0 ? styles.good : ''}>
                      {diff != null ? (diff > 0 ? `+${diff}` : diff) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className={styles.chartNote}>
          Diff = Warm ERA − Cold ERA. Positive = worse in heat, negative = better in heat.
          Sample sizes are small — interpret individual pitcher splits with caution.
        </p>
      </Section>

      {/* ── Methodology ── */}
      <div className={styles.methodology}>
        <h2 className={styles.methodTitle}>Methodology & Limitations</h2>
        <p>{meta.note}</p>
        <div className={styles.methodGrid}>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Data source</span>
            <span>MLB Stats API (statsapi.mlb.com) — official MLB data, no API key required</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Statistical test</span>
            <span>Pearson correlation coefficient between game-day temperature (°F) and per-start ERA</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Known confounders</span>
            <span>Opposition quality, home/away, pitcher fatigue, bullpen usage — temperature is not isolated</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Rate calculation</span>
            <span>Aggregate ERA = Σ(ER) × 9 / Σ(IP), not mean of per-game ERAs</span>
          </div>
        </div>
      </div>

    </div>
  )
}

function Section({ title, subtitle, children }) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        {subtitle && <p className={styles.sectionSub}>{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function FindingCard({ label, value, sub, highlight }) {
  return (
    <div className={`${styles.findingCard} ${styles[`hl_${highlight}`]}`}>
      <div className={styles.findingLabel}>{label}</div>
      <div className={styles.findingValue}>{value}</div>
      {sub && <div className={styles.findingSub}>{sub}</div>}
    </div>
  )
}
