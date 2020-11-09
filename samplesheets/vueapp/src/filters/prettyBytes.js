import Vue from 'vue'

// Adapted from https://gist.github.com/james2doyle/4aba55c22f084800c199
Vue.filter('prettyBytes', function (num) {
  // jacked from: https://github.com/sindresorhus/pretty-bytes
  if (typeof num !== 'number' || isNaN(num)) {
    throw new TypeError('Expected a number')
  }

  const neg = num < 0
  const units = ['B', 'kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

  if (neg) num = -num
  if (num < 1) return (neg ? '-' : '') + num + ' B'

  const exponent = Math.min(Math.floor(Math.log(num) / Math.log(1000)), units.length - 1)
  num = (num / Math.pow(1000, exponent)).toFixed(2) * 1
  const unit = units[exponent]

  return (neg ? '-' : '') + num + ' ' + unit
})
