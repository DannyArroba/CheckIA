import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const colors = { Bajo: '#10b981', Medio: '#f59e0b', Alto: '#ef4444' }

export default function DashboardCharts({ summary, cities, providers }) {
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <ChartPanel title="Distribución de riesgo">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={summary.risk_distribution || []} dataKey="count" nameKey="risk_level" outerRadius={92} label>
              {(summary.risk_distribution || []).map((entry) => <Cell key={entry.risk_level} fill={colors[entry.risk_level] || '#64748b'} />)}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </ChartPanel>
      <ChartPanel title="Casos por ciudad">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(cities || []).slice(0, 8)}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="city" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="claims" fill="#1f6fff" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
      <ChartPanel title="Ranking de proveedores">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={(providers || []).slice(0, 7)} layout="vertical" margin={{ left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" />
            <YAxis dataKey="provider_name" type="category" tick={{ fontSize: 11 }} width={110} />
            <Tooltip />
            <Bar dataKey="alerts" fill="#f59e0b" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    </div>
  )
}

function ChartPanel({ title, children }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft"><h3 className="mb-4 font-bold text-ink">{title}</h3>{children}</div>
}
