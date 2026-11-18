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
      traditional: true,
      success: function (data) {
        $('span.sodar-irods-stats').each(function () {
          let path = $(this).attr('data-stats-path')
          let s = 's'
          if (path in data['irods_stats']) {
            let status = data['irods_stats'][path]['status']
            if (status === 200) {
              $(this).removeClass('badge-danger').addClass(
                'badge-info')
              let fileCount = data['irods_stats'][path][
                'file_count'
              ]
              let totalSize = data['irods_stats'][path][
                'total_size'
              ]
              if (fileCount === 1) s = ''
              $(this).text(
                fileCount + ' file' + s +
                ' (' + humanFileSize(totalSize, true) + ')')
            } else {
              $(this).removeClass('badge-info').addClass(
                'badge-danger')
              if (status === 404) $(this).text('Not found')
              else if (status === 403) $(this).text('Denied')
              else $(this).text('Error')
            }
          }
        })
      },
      error: function () {
        $('span.sodar-irods-stats').each(function () {
          $(this).removeClass('badge-info').addClass(
            'badge-danger')
          $(this).text('Error')
        })
      }
    })
  })
}

/***********************
 Periodic status update
************************/
let setPeriodicStatsUpdate = function () {
  updateCollectionStats()
  let statsSec = 8
  if (typeof (window.irodsbackendStatusInterval) !== 'undefined') {
    statsSec = window.irodsbackendStatusInterval
  }
  let statsInterval = statsSec * 1000
  // Poll and update active collections
  setInterval(function () {
    updateCollectionStats()
  }, statsInterval)
}

/******************************************
 Toggling items in one dropdown function
 ******************************************/
//enables or disables every .sodar-irods-*-item in a dropdown
let toggleDropdownItems = function (row, status, stats) {
  $(row).find('a.dropdown-item').each(function () {
    if (status === '200') {
      $(this).removeClass('disabled')
      // $(this).tooltip('enable')

      //collection is empty; disable all but the copy path buttons
      if (stats['file_count'] === 0) {
        if ($(this).is('.sodar-irods-dav-item')) {
          $(this).addClass('disabled')
          // $(this).tooltip('disable')
        }
      }
    }
    //collection doesn't exist; disable all buttons
    else {
      $(this).addClass('disabled')
    }
  })
}

/***************************************
 Collection buttons updating function
 ***************************************/
let updateButtons = function () {
  let ipaths = []
  let projectUUID = ''

  $('button.sodar-irods-path-item').each(function () {
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
        contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
        traditional: true
      }).done(function (data) {
        $('a.sodar-irods-path-item').each(function () {
          let itemPath = $(this).attr('data-clipboard-text')
          let parentDropdown = $(this).closest(
            '.sodar-irods-dropdown')
          for (idx in data['coll_objects']) {
            if (data['coll_objects'].hasOwnProperty(idx)) {
              if (itemPath === data['coll_objects'][idx]['path']) {
                let status = data['coll_objects'][idx]['status']
                let stats = data['coll_objects'][idx]['stats']
                toggleDropdownItems(parentDropdown, status, stats)
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
  parentButton = elem.closest('.sodar-irods-dropdown').find('button')
  parentButton.addClass('text-warning')
  elem.delay(250).queue(function () {
    parentButton.removeClass('text-warning').dequeue()
  })
}

$(document).ready(function () {
  // Init Clipboards
  new ClipboardJS('.sodar-irods-copy-item')
  // Add copy link handler
  $('.sodar-irods-copy-item').click(function () {
    displayCopyStatus($(this))
  })
})
