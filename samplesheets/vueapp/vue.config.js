const BundleTracker = require('webpack-bundle-tracker')
const DEPLOYMENT_PATH = '/static/'

module.exports = {
  publicPath: process.env.NODE_ENV === 'production' ? DEPLOYMENT_PATH : 'http://localhost:8080/',
  outputDir: './dist/',
  assetsDir: 'samplesheets-vue/',
  devServer: {
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  },
  // productionSourceMap: false,

  configureWebpack: {
    plugins: [
      new BundleTracker({ path: __dirname, filename: './webpack-stats.json' })
    ]
  }
}
