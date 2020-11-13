// Miscellaneous testing utilities

// Bootstrap-vue modal helpers
// From: https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/tests/utils.js
export const createContainer = (tag = 'div') => {
  const container = document.createElement(tag)
  document.body.appendChild(container)
  return container
}
export const waitNT = ctx => new Promise(resolve => ctx.$nextTick(resolve))
export const waitRAF = () => new Promise(resolve => requestAnimationFrame(resolve))
