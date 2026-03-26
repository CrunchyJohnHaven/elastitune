export function plugin() {
  return {
    setup(core: any) {
      core.application.register({
        id: 'elastitune',
        title: 'ElastiTune',
        mount: async () => {
          const container = document.createElement('div');
          container.style.padding = '24px';
          container.innerHTML = `
            <h2>ElastiTune</h2>
            <p>Open the standalone ElastiTune control plane to optimize an Elasticsearch index.</p>
            <a href="http://localhost:8000" target="_blank" rel="noreferrer">Launch ElastiTune</a>
          `;
          document.body.appendChild(container);
          return () => container.remove();
        },
      });
    },
    start() {},
    stop() {},
  };
}
