/***************************************
 Collection statistics updating function
 ***************************************/
let updateCollectionStats = function () {
  let paths = {}

  $('span.sodar-irods-stats').each(function () {
    let projectUUID = $(this).attr('data-project-uuid')
    if (!paths.hasOwnProperty(projectUUID)) {
      paths[projectUUID] = []
    }
    let currentPath = $(this).attr('data-stats-path')
    if (!(paths[projectUUID].includes(currentPath))) {
      paths[projectUUID].push(currentPath)
    }
  })

  $.each(paths, function (projectUUID, paths) {
    $.ajax({
      url: '/irodsbackend/ajax/stats/' + projectUUID,
      method: 'POST',
      dataType: 'json',
      data: {
        paths: paths
      },
      contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
      traditional: true
    }).done(function (data) {
      $('span.sodar-irods-stats').each(function () {
        let statsSpan = $(this)
        let path = statsSpan.attr('data-stats-path')
        let s = 's'
        if (path in data['irods_stats']) {
          let status = data['irods_stats'][path]['status']
          if (status === 200) {
            let fileCount = data['irods_stats'][path][
              'file_count']
            let totalSize = data['irods_stats'][path][
              'total_size']
            if (fileCount === 1) s = ''
            statsSpan.text(
              fileCount + ' file' + s +
              ' (' + humanFileSize(totalSize, true) + ')')
          } else if (status === 404) statsSpan.text('Not found')
          else if (status === 403) statsSpan.text('Denied')
          else statsSpan.text('Error')
        }
      })
    })
  })
}

/***************************************
 Toggling buttons in one row function
 ***************************************/
//enables or disables every .sodar-list-btn button in a row
let toggleButtons = function (row, status, stats) {
  $(row).find('.sodar-list-btn').each(function () {
    if (status === '200') {
      if ($(this).is('button')) {
        $(this).removeAttr('disabled')
      }
      $(this).removeClass('disabled')
      // $(this).tooltip('enable')

      //collection is empty; disable all but the copy path buttons
      if (stats['file_count'] === 0) {
        if ($(this).is('.sodar-irods-dav-btn')) {
          $(this).addClass('disabled')
          // $(this).tooltip('disable')
        }
      }
    }
    //collection doesn't exist; disable all buttons
    else {
      if ($(this).is('button')) {
        $(this).attr('disabled', 'disabled')
      } else if ($(this).is('a')) {
        $(this).addClass('disabled')
      }
    }
  })
}

/***************************************
 Collection buttons updating function
 ***************************************/
let updateButtons = function () {
  let ipaths = []
  let projectUUID = ''

  $('button.sodar-irods-path-btn').each(function () {
    if (!$(this).hasClass('no-colls')) {
      let buttonPath = $(this).attr('data-clipboard-text')
      projectUUID = buttonPath.split('/')[4]
      if (!(ipaths.includes(buttonPath))) {
        ipaths.push(buttonPath)
      }
    }
  })
  let pathCount = ipaths.length
  let batchSize = window.irodsQueryBatchSize
  let batchStart = 0
  let pathBatch = []

  // Query in batches
  while (batchStart < pathCount) {
    if (pathCount < (batchStart + batchSize)) {
      pathBatch = ipaths.slice(batchStart, pathCount)
    } else {
      pathBatch = ipaths.slice(batchStart, batchStart + batchSize)
    }
    batchStart = batchStart + batchSize
    let d = {
      paths: pathBatch
    }

    if (projectUUID !== '') {
      $.ajax({
        url: '/irodsbackend/ajax/stats/' + projectUUID,
        method: 'POST',
        dataType: 'json',
        data: d,
        contentType: "application/x-www-form-urlencoded; charset=UTF-8",
        traditional: true
      }).done(function (data) {
        $('button.sodar-irods-path-btn').each(function () {
          let buttonPath = $(this).attr('data-clipboard-text')
          let buttonRow = $(this).closest('span')
          for (idx in data['coll_objects']) {
            if (data['coll_objects'].hasOwnProperty(idx)) {
              if (buttonPath === data['coll_objects'][idx]['path']) {
                let status = data['coll_objects'][idx]['status']
                let stats = data['coll_objects'][idx]['stats']
                toggleButtons(buttonRow, status, stats)
                break
              }
            }
          }
        })
      })
    }
  }
}

/************************
 Copy path display method
*************************/
function displayCopyStatus(elem) {
  elem.addClass('text-warning')
  elem.delay(250).queue(function () {
    elem.removeClass('text-warning').dequeue()
  })
}

$(document).ready(function () {
  // Init Clipboards
  new ClipboardJS('.sodar-irods-copy-btn')
  // Add copy link handler
  $('.sodar-irods-copy-btn').click(function () {
    displayCopyStatus($(this))
  })
})
