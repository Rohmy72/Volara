import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export default function PriceChart({ priceSeries }) {
  // Scatter must read from the SAME array (same length/index alignment) as
  // Line when both share a categorical (date) x-axis inside a ComposedChart.
  // Passing Scatter a separately-filtered, shorter array breaks x/y alignment
  // because Recharts maps category positions by index into the shared axis.
  const chartData = priceSeries.map((p) => ({
    ...p,
    newsClose: p.is_news_day ? p.close : null,
  }));

  return (
    <div className="chart-card">
      <h3>Price, with news days marked</h3>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11 }}
            width={60}
          />
          <Tooltip
            formatter={(value, name) => [typeof value === "number" ? value.toFixed(2) : value, name]}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="close"
            name="Close price"
            stroke="var(--chart-line, #92ad63)"
            dot={false}
            strokeWidth={1.75}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="newsClose"
            name="News day"
            fill="var(--chart-news-dot, #e8734a)"
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
