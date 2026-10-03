// Endereço do serviço de contagem do site (Cloudflare Worker sf-site). É o único sítio onde está: para o trocar, muda-se só esta linha.
// Vazio ('') = sem serviço: as ligações dos PDFs voltam a apontar para reports/ e não se conta nada.
window.SF_W = 'https://sf-site.sergiofpt.workers.dev';
