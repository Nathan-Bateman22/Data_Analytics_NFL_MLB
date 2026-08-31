import useRoster from '../hooks/useRoster'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'
import styles from './InjuryAnalysis.module.css'

const GRASS_COLOR = '#4CAF50'
const TURF_COLOR  = '#2196F3'
const GRASS_LIGHT = '#81C784'
const TURF_LIGHT  = '#64B5F6'

const FMT = v => (typeof v === 'number' ? v.toFixed(3) : v)

export default function InjuryAnalysis() {
  const { data, loading, error } = useRoster('/api/nfl/injuries/')

  if (loading) return <LoadingSpinner color="#69BE28" message="Running injury analysis — this may take 30–60 s on first load…" />
  if (error)   return <div className={styles.error}>Failed to load analysis: {error}</div>

  const { meta, overall, by_season, by_injury_type, by_position } = data

  const overviewChartData = [
    {
      name: 'Non-Contact\n(Soft Tissue)',
      label: 'Non-Contact',
      Grass: overall.grass.non_contact.rate,
      Turf:  overall.turf.non_contact.rate,
    },
    {
      name: 'Contact\n(Traumatic)',
      label: 'Contact',
      Grass: overall.grass.contact.rate,
      Turf:  overall.turf.contact.rate,
    },
  ]

  const chi2 = overall.chi_square
  const rr_nc = overall.rate_ratio.non_contact
  const rr_c  = overall.rate_ratio.contact

  return (
    <div className={styles.page}>

      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerEyebrow}>NFL · Analytics</div>
        <h1 className={styles.headerTitle}>Surface & Injury Analysis</h1>
        <p className={styles.headerSub}>
          Non-contact vs. contact injury rates on natural grass vs. artificial turf · {meta.seasons}
        </p>
      </div>

      {/* ── Key Findings ── */}
      <div className={styles.findingsGrid}>
        <FindingCard
          label="Total Classified Injuries"
          value={meta.total_classified.toLocaleString()}
          sub={meta.seasons}
        />
        <FindingCard
          label="Chi-Square p-value"
          value={chi2.p_value.toFixed(4)}
          sub={chi2.significant ? '★ Significant (p < 0.05)' : 'Not significant (p ≥ 0.05)'}
          highlight={chi2.significant ? 'pos' : 'neutral'}
        />
        <FindingCard
          label="Non-Contact Rate Ratio"
          value={rr_nc.value ?? '—'}
          sub={rr_nc.value ? `95% CI [${rr_nc.ci_lower}, ${rr_nc.ci_upper}]  Turf vs Grass` : 'insufficient data'}
          highlight={rr_nc.value && rr_nc.value > 1 ? 'neg' : 'neutral'}
        />
        <FindingCard
          label="Contact Rate Ratio"
          value={rr_c.value ?? '—'}
          sub={rr_c.value ? `95% CI [${rr_c.ci_lower}, ${rr_c.ci_upper}]  Turf vs Grass` : 'insufficient data'}
          highlight="neutral"
        />
      </div>

      {/* ── Overall rates chart ── */}
      <Section title="Injury Rates by Surface Type" subtitle="Injuries per 1,000 player-game exposures">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={overviewChartData} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="label" tick={{ fill: '#a0adb8', fontSize: 13 }} />
            <YAxis tick={{ fill: '#a0adb8', fontSize: 12 }} tickFormatter={v => v.toFixed(3)} />
            <Tooltip
              contentStyle={{ background: '#0d1b2a', border: '1px solid #1e3a5f', borderRadius: 8 }}
              labelStyle={{ color: '#e0e7ef' }}
              itemStyle={{ color: '#e0e7ef' }}
              formatter={(v, name) => [v.toFixed(4), name]}
            />
            <Legend wrapperStyle={{ color: '#a0adb8' }} />
            <Bar dataKey="Grass" fill={GRASS_COLOR} radius={[4, 4, 0, 0]} />
            <Bar dataKey="Turf"  fill={TURF_COLOR}  radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className={styles.chartNote}>
          Rate Ratio (Turf vs Grass) — Non-Contact: {rr_nc.value ?? 'N/A'} · Contact: {rr_c.value ?? 'N/A'}.
          Chi-square χ²({chi2.dof}) = {chi2.statistic}, p = {chi2.p_value.toFixed(4)}.
          {!chi2.significant && ' No statistically significant surface effect detected at α = 0.05.'}
        </p>
      </Section>

      {/* ── Season trends ── */}
      <Section title="Injury Rate Trends by Season" subtitle="How rates have changed 2016 – 2024">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={by_season} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="season" tick={{ fill: '#a0adb8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#a0adb8', fontSize: 12 }} tickFormatter={v => v.toFixed(3)} />
            <Tooltip
              contentStyle={{ background: '#0d1b2a', border: '1px solid #1e3a5f', borderRadius: 8 }}
              labelStyle={{ color: '#e0e7ef' }}
              itemStyle={{ color: '#e0e7ef' }}
              formatter={(v, name) => [v.toFixed(4), name]}
            />
            <Legend wrapperStyle={{ color: '#a0adb8' }} />
            <Line type="monotone" dataKey="grass_non_contact_rate" name="Grass · Non-Contact" stroke={GRASS_COLOR}  strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="turf_non_contact_rate"  name="Turf · Non-Contact"  stroke={TURF_COLOR}   strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="grass_contact_rate"     name="Grass · Contact"     stroke={GRASS_LIGHT}  strokeWidth={2} dot={{ r: 3 }} strokeDasharray="5 3" />
            <Line type="monotone" dataKey="turf_contact_rate"      name="Turf · Contact"      stroke={TURF_LIGHT}   strokeWidth={2} dot={{ r: 3 }} strokeDasharray="5 3" />
          </LineChart>
        </ResponsiveContainer>
        <p className={styles.chartNote}>
          Dashed lines = contact injuries. Solid lines = non-contact. Note the 2020 COVID-shortened season may affect rates.
        </p>
      </Section>

      {/* ── By specific injury type ── */}
      <Section title="Rate by Specific Injury Type" subtitle="Injuries per 1,000 player-game exposures · Turf vs Grass">
        <ResponsiveContainer width="100%" height={360}>
          <BarChart
            data={by_injury_type}
            layout="vertical"
            margin={{ top: 5, right: 40, left: 90, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis type="number" tick={{ fill: '#a0adb8', fontSize: 12 }} tickFormatter={v => v.toFixed(3)} />
            <YAxis type="category" dataKey="injury" tick={{ fill: '#a0adb8', fontSize: 13 }} width={85} />
            <Tooltip
              contentStyle={{ background: '#0d1b2a', border: '1px solid #1e3a5f', borderRadius: 8 }}
              labelStyle={{ color: '#e0e7ef' }}
              itemStyle={{ color: '#e0e7ef' }}
              formatter={(v, name) => [v.toFixed(4), name]}
            />
            <Legend wrapperStyle={{ color: '#a0adb8' }} />
            <Bar dataKey="grass_rate" name="Grass" fill={GRASS_COLOR} radius={[0, 3, 3, 0]} />
            <Bar dataKey="turf_rate"  name="Turf"  fill={TURF_COLOR}  radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className={styles.rrTable}>
          <table>
            <thead>
              <tr>
                <th>Injury</th>
                <th>Grass rate</th>
                <th>Turf rate</th>
                <th>Rate Ratio (Turf/Grass)</th>
                <th>95% CI</th>
              </tr>
            </thead>
            <tbody>
              {by_injury_type.map(row => (
                <tr key={row.injury}>
                  <td>{row.injury}</td>
                  <td>{row.grass_rate.toFixed(4)}</td>
                  <td>{row.turf_rate.toFixed(4)}</td>
                  <td className={row.rate_ratio > 1.1 ? styles.higher : row.rate_ratio < 0.9 ? styles.lower : ''}>
                    {row.rate_ratio?.toFixed(3) ?? '—'}
                  </td>
                  <td className={styles.ci}>
                    {row.ci_lower && row.ci_upper ? `[${row.ci_lower}, ${row.ci_upper}]` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {/* ── By position group ── */}
      <Section title="Non-Contact Injury Rate by Position" subtitle="Soft-tissue injuries per 1,000 player-game exposures">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={by_position} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="position" tick={{ fill: '#a0adb8', fontSize: 13 }} />
            <YAxis tick={{ fill: '#a0adb8', fontSize: 12 }} tickFormatter={v => v.toFixed(3)} />
            <Tooltip
              contentStyle={{ background: '#0d1b2a', border: '1px solid #1e3a5f', borderRadius: 8 }}
              labelStyle={{ color: '#e0e7ef' }}
              itemStyle={{ color: '#e0e7ef' }}
              formatter={(v, name) => [v.toFixed(4), name]}
            />
            <Legend wrapperStyle={{ color: '#a0adb8' }} />
            <Bar dataKey="grass_non_contact_rate" name="Grass · Non-Contact" fill={GRASS_COLOR} radius={[4,4,0,0]} />
            <Bar dataKey="turf_non_contact_rate"  name="Turf · Non-Contact"  fill={TURF_COLOR}  radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className={styles.chartNote}>
          Denominator = total player-game exposures per surface (not position-specific roster size).
          Rate comparisons between positions should be interpreted with caution.
        </p>
      </Section>

      {/* ── Methodology ── */}
      <div className={styles.methodology}>
        <h2 className={styles.methodTitle}>Methodology & Limitations</h2>
        <p>{meta.methodology}</p>
        <div className={styles.methodGrid}>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Data source</span>
            <span>{meta.data_source}</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Statistical tests</span>
            <span>Pearson chi-square (2×2 contingency table); Poisson rate ratio with Wald 95% CI</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Exposure denominator</span>
            <span>46 active players × team-game appearances per surface type</span>
          </div>
          <div className={styles.methodItem}>
            <span className={styles.methodLabel}>Injury classification</span>
            <span>Keyword matching on primary injury field; unclassified entries excluded</span>
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
    <div className={`${styles.findingCard} ${highlight ? styles[`highlight_${highlight}`] : ''}`}>
      <div className={styles.findingLabel}>{label}</div>
      <div className={styles.findingValue}>{value}</div>
      {sub && <div className={styles.findingSub}>{sub}</div>}
    </div>
  )
}
