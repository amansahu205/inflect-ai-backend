export const formatCurrency = (n: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(n);

export const formatPercent = (n: number) =>
  `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

export const formatDate = (s: string) =>
  new Date(s).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

export const formatNumber = (n: number) =>
  new Intl.NumberFormat('en-US').format(n);
