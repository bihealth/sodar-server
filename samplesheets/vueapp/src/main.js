import Vue from 'vue'
import App from './App'
import router from './router'
import '../node_modules/ag-grid-community/dist/styles/ag-grid.css'
import '../node_modules/ag-grid-community/dist/styles/ag-theme-bootstrap.css'

import BootstrapVue from 'bootstrap-vue'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import VueClipboard from 'vue-clipboard2'

Vue.use(BootstrapVue)
VueClipboard.config.autoSetContainer = true
Vue.use(VueClipboard)

Vue.config.productionTip = false

// Global template filters

// From https://stackoverflow.com/a/35071765
// Credit to @Bill Criswell for this filter
Vue.filter(
  'truncate',
  function (text, stop, clamp) {
    return text.slice(0, stop) + (stop < text.length ? clamp || '...' : '')
  }
)

// Adapted from https://gist.github.com/james2doyle/4aba55c22f084800c199
Vue.filter('prettyBytes', function (num) {
  // jacked from: https://github.com/sindresorhus/pretty-bytes
  if (typeof num !== 'number' || isNaN(num)) {
    throw new TypeError('Expected a number')
  }

  const neg = num < 0
  const units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

  if (neg) {
    num = -num
  }

  if (num < 1) {
    return (neg ? '-' : '') + num + ' B'
  }

  const exponent = Math.min(Math.floor(Math.log(num) / Math.log(1000)), units.length - 1)
  num = (num / Math.pow(1000, exponent)).toFixed(2) * 1
  const unit = units[exponent]

  return (neg ? '-' : '') + num + ' ' + unit
})

new Vue({
  router,
  render: h => h(App)
}).$mount('#app')
