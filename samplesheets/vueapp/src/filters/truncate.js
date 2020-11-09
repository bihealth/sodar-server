import Vue from 'vue'

// From https://stackoverflow.com/a/35071765
// Credit to @Bill Criswell for this filter
Vue.filter(
  'truncate',
  function (text, stop, clamp) {
    return text.slice(0, stop) + (stop < text.length ? clamp || '...' : '')
  }
)
