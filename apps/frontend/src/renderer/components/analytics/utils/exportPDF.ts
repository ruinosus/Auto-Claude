/**
 * Export analytics data as a printable report.
 * Opens a new window with formatted content that can be printed/saved as PDF.
 */
export interface ExportData {
  title: string;
  generatedAt: Date;
  investment: number;
  valueGenerated: number;
  netSavings: number;
  roi: number;
  hoursImpact: number;
  topSpecs: { name: string; value: number; roi: number }[];
}

export function exportToPDF(data: ExportData): void {
  const formatCurrency = (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
  const formatPercent = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(0)}%`;

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>${data.title}</title>
      <style>
        body { font-family: system-ui, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
        h1 { color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }
        .generated { color: #666; font-size: 12px; margin-bottom: 30px; }
        .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }
        .metric { background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 28px; font-weight: bold; color: #1e40af; }
        .metric-label { font-size: 12px; color: #666; margin-top: 5px; }
        .roi-highlight { background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 30px 0; }
        .roi-value { font-size: 48px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
        th { background: #f9fafb; font-weight: 600; }
        .positive { color: #16a34a; }
        .negative { color: #dc2626; }
        @media print { body { padding: 20px; } }
      </style>
    </head>
    <body>
      <h1>${data.title}</h1>
      <p class="generated">Generated: ${data.generatedAt.toLocaleString()}</p>

      <div class="roi-highlight">
        <div class="roi-value">${formatPercent(data.roi)}</div>
        <div>Return on Investment</div>
      </div>

      <div class="metrics">
        <div class="metric">
          <div class="metric-value">${formatCurrency(data.investment)}</div>
          <div class="metric-label">Total Investment</div>
        </div>
        <div class="metric">
          <div class="metric-value">${formatCurrency(data.valueGenerated)}</div>
          <div class="metric-label">Value Generated</div>
        </div>
        <div class="metric">
          <div class="metric-value">${formatCurrency(data.netSavings)}</div>
          <div class="metric-label">Net Savings</div>
        </div>
      </div>

      <div class="metric" style="margin: 20px 0;">
        <div class="metric-value">${data.hoursImpact.toFixed(1)}h</div>
        <div class="metric-label">Developer Hours Saved (≈ ${(data.hoursImpact / 160).toFixed(1)} FTE-months)</div>
      </div>

      <h2>Top Performing Specs</h2>
      <table>
        <thead>
          <tr><th>Spec</th><th>Value</th><th>ROI</th></tr>
        </thead>
        <tbody>
          ${data.topSpecs
            .map(
              (spec) => `
            <tr>
              <td>${spec.name}</td>
              <td>${formatCurrency(spec.value)}</td>
              <td class="${spec.roi >= 0 ? 'positive' : 'negative'}">${formatPercent(spec.roi)}</td>
            </tr>
          `
            )
            .join('')}
        </tbody>
      </table>

      <script>window.print();</script>
    </body>
    </html>
  `;

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(html);
    printWindow.document.close();
  }
}
