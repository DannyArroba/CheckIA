import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const colors = { Bajo: '#10b981', Medio: '#f59e0b', Alto: '#ef4444', Critico: '#9f1239' }

export default function DashboardCharts({
  summary,
  cities,
  providers,
  selectedRisk,
  selectedCity,
  selectedProvider,
  onRiskSelect,
  onCitySelect,
  onProviderSelect
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <ChartPanel title="Distribución de riesgo" helper="Clic en un segmento para filtrar la bandeja inferior.">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={summary.risk_distribution || []}
              dataKey="count"
              nameKey="risk_level"
              outerRadius={92}
              label
              onClick={(entry) => onRiskSelect?.(entry.risk_level)}
              cursor="pointer"
            >
              {(summary.risk_distribution || []).map((entry) => (
                <Cell
                  key={entry.risk_level}
                  fill={colors[entry.risk_level] || '#64748b'}
                  stroke={selectedRisk === entry.risk_level ? '#10233f' : '#ffffff'}
                  strokeWidth={selectedRisk === entry.risk_level ? 3 : 1}
                />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </ChartPanel>
      <ChartPanel title="Casos por ciudad" helper="Clic en una barra para combinar filtro por ciudad.">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(cities || []).slice(0, 8)}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="city" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="claims" radius={[6, 6, 0, 0]} cursor="pointer" onClick={(entry) => onCitySelect?.(entry?.city || entry?.payload?.city)}>
              {(cities || []).slice(0, 8).map((entry) => (
                <Cell key={entry.city} fill={selectedCity === entry.city ? '#10233f' : '#1f6fff'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
      <ChartPanel title="Ranking de proveedores" helper="Clic en una barra para combinar filtro por proveedor.">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(providers || []).slice(0, 7)} layout="vertical" margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" />
            <YAxis dataKey="provider_name" type="category" tick={{ fontSize: 11 }} width={110} />
            <Tooltip />
            <Bar dataKey="alerts" radius={[0, 6, 6, 0]} cursor="pointer" onClick={(entry) => onProviderSelect?.(entry?.provider_name || entry?.payload?.provider_name)}>
              {(providers || []).slice(0, 7).map((entry) => (
                <Cell key={entry.provider_name} fill={selectedProvider === entry.provider_name ? '#10233f' : '#f59e0b'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    </div>
  )
}

function ChartPanel({ title, helper, children }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
      <h3 className="font-bold text-ink">{title}</h3>
      {helper && <p className="mt-1 text-xs text-slate-500">{helper}</p>}
      <div className="mt-4">{children}</div>
    </div>
  )
}
