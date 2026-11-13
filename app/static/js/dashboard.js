const canvas = document.querySelector('#activity-chart');
const data = document.querySelector('#chart-data');
if (canvas && data && window.Chart) {
  const activity = JSON.parse(data.textContent);
  new Chart(canvas, {
    type: 'bar',
    data: { labels: activity.labels, datasets: [{ label: 'Operaciones confirmadas', data: activity.values, backgroundColor: '#607d65', hoverBackgroundColor: '#173b35', borderRadius: 3, maxBarThickness: 27 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 200 },
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#173b35', padding: 10 } },
      scales: {
        y: { beginAtZero: true, suggestedMax: 4, border: { display: false }, grid: { color: '#eff1ea' }, ticks: { precision: 0, font: { family: 'Inter', size: 9 }, color: '#8c9587' } },
        x: { border: { display: false }, grid: { display: false }, ticks: { color: '#8c9587', font: { family: 'Inter', size: 9 } } }
      }
    }
  });
}
