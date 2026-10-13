import { defineConfig } from 'vitepress'

const zhSidebar = [
  { text: '开始使用', items: [{ text: '概览', link: '/zh/' }, { text: '应用与扫描', link: '/zh/application' }] },
  { text: '核心容器', items: [{ text: 'Bean、注入与生命周期', link: '/zh/beans' }, { text: '依赖注入 Autowired', link: '/zh/dependency-injection' }, { text: '配置与自动配置', link: '/zh/configuration' }] },
  { text: 'Web', items: [{ text: '路由、异常与上下文', link: '/zh/web' }] },
  { text: '横切能力', items: [{ text: 'AOP', link: '/zh/aop' }, { text: '事务', link: '/zh/transactions' }, { text: '任务执行', link: '/zh/tasks' }] },
  { text: '参考', items: [{ text: '完整 API 参数', link: '/zh/api-reference' }, { text: 'PythonBoot / Spring Boot 对照', link: '/zh/spring-comparison' }] }
]

const enSidebar = [
  { text: 'Getting started', items: [{ text: 'Overview', link: '/en/' }, { text: 'Application and scanning', link: '/en/application' }] },
  { text: 'Core container', items: [{ text: 'Beans, injection and lifecycle', link: '/en/beans' }, { text: 'Dependency injection / Autowired', link: '/en/dependency-injection' }, { text: 'Configuration and auto-configuration', link: '/en/configuration' }] },
  { text: 'Web', items: [{ text: 'Routes, errors and context', link: '/en/web' }] },
  { text: 'Cross-cutting', items: [{ text: 'AOP', link: '/en/aop' }, { text: 'Transactions', link: '/en/transactions' }, { text: 'Task execution', link: '/en/tasks' }] },
  { text: 'Reference', items: [{ text: 'Complete API parameters', link: '/en/api-reference' }, { text: 'PythonBoot / Spring Boot comparison', link: '/en/spring-comparison' }] }
]

export default defineConfig({
  title: 'PythonBoot',
  description: 'FastAPI-based backend framework inspired by Spring Boot',
  cleanUrls: true,
  locales: {
    root: { label: '简体中文', lang: 'zh-CN', link: '/zh/' },
    en: { label: 'English', lang: 'en-US', link: '/en/' }
  },
  themeConfig: {
    nav: [
      { text: '中文', link: '/zh/' },
      { text: 'English', link: '/en/' },
      { text: 'GitHub', link: 'https://github.com/' }
    ],
    sidebar: { '/zh/': zhSidebar, '/en/': enSidebar },
    socialLinks: [],
    search: { provider: 'local' }
  }
})
