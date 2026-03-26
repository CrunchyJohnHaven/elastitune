export function plugin() {
  return {
    setup(core: any) {
      core.application.register({
        id: 'elastitune',
        title: 'ElastiTune',
        mount: async (params: any) => {
          const [{ renderApp }] = await Promise.all([
            import('./render_app'),
          ]);
          return renderApp(core, params);
        },
      });
    },
    start() {},
    stop() {},
  };
}
