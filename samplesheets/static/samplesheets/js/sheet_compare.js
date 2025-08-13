function buildDiffCard(category, filename, counter, table, url, source,
target) {
  return `
    <div class="card" id="sodar-ss-${category}-diff${counter}">
      <div class="card-header">
        <h4>
          ${filename}
          <a href="${url}?source=${source}&target=${target}&category=${category}&filename=${filename}"
             target="_blank"
             class="btn btn-secondary sodar-header-button sodar-ss-diff-btn pull-right"
             title="Open table in a new window">
            <i class="iconify" data-icon="mdi:open-in-new"></i>
          </a>
        </h4>
      </div>
      <div class="card-body p-0 table-responsive sodar-ss-diff-card-body">
        ${table}
      </div>
    </div>
  `
}


function buildDiffPage(ajaxUrl, url, source, target) {
  $.ajax({
    url: ajaxUrl + '?source=' + source + '&target=' + target
  }).done(function (data) {
    for (let category in data) {
      let counter = 0
      for (let filename in data[category]) {
        let table = buildDiffTable(data[category][filename])
        let card = buildDiffCard(
          category, filename, counter, table, url, source, target)
        $('#sodar-ss-diff-container').append(card)
        counter++
      }
    }
  })
}


function buildFilePage(ajaxUrl, source, target, filename, category) {
  $.ajax({
    url: ajaxUrl + '?source=' + source + '&target=' + target +
      '&filename=' + filename + '&category=' + category
  }).done(function (data) {
    let table = buildDiffTable(data)
    $('#sodar-ss-diff-container').append(table)
  })
}


function buildDiffTable(data) {
  let table1 = new daff.TableView(data[0])
  let table2 = new daff.TableView(data[1])
  table1.trim()
  table2.trim()
  let alignment = daff.compareTables(table1, table2).align()
  let data_diff = []
  let table_diff = new daff.TableView(data_diff)
  let flags = new daff.CompareFlags()
  flags.show_unchanged = false
  flags.always_show_header = false
  let highlighter = new daff.TableDiff(alignment, flags)
  highlighter.hilite(table_diff)
  let diff2html = new daff.DiffRender()
  diff2html.render(table_diff)
  return diff2html.html()
}
