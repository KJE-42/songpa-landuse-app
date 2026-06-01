import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { getLanduseColorHex } from '../utils/colors';
import { formatArea, formatCount, formatPercent } from '../utils/format';

function LanduseChart({ rows, countLabel }) {
  const chartRows = rows.filter((row) => row.area_m2 > 0);

  if (chartRows.length === 0) {
    return (
      <div className="chart-card chart-card--empty">
        <h3>토지이용 구성비</h3>
        <p>차트를 그릴 수 있는 집계 데이터가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="chart-card">
      <div className="chart-card__header">
        <h3>토지이용 구성비</h3>
        <span>현재 표와 동일한 집계 기준</span>
      </div>
      <div className="chart-card__body">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={chartRows}
              dataKey="area_m2"
              nameKey="landuse_group"
              innerRadius={62}
              outerRadius={96}
              paddingAngle={1}
              labelLine={false}
              label={({ name, percent }) =>
                percent >= 0.04 ? `${name} ${formatPercent(percent * 100)}%` : ''
              }
            >
              {chartRows.map((row) => (
                <Cell
                  key={row.landuse_group}
                  fill={getLanduseColorHex(row.landuse_group)}
                />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip countLabel={countLabel} />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ChartTooltip({ active, payload, countLabel }) {
  if (!active || !payload?.length) {
    return null;
  }

  const row = payload[0].payload;
  const countValue = countLabel === '필지 수' ? row.parcel_count : row.building_count;

  return (
    <div className="chart-tooltip">
      <strong>{row.landuse_group}</strong>
      <div>면적: {formatArea(row.area_m2)}㎡</div>
      <div>구성비: {formatPercent(row.ratio)}%</div>
      <div>
        {countLabel}: {formatCount(countValue)}
      </div>
    </div>
  );
}

export default LanduseChart;

