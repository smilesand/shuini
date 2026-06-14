import type { App, Component } from 'vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'


export function registerAppIcons(app: App<Element>): void {
  for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(name, component as Component)
  }
}