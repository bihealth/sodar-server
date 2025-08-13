// Init global variable
let isSuperuser = false

/*********************
 Zone status updating
 *********************/
let updateZoneStatus = function () {
  window.zoneStatusUpdated = false
  let zoneData = {}
  let createLimitBadge = $('#sodar-lz-badge-create-limit')
  let validateLimitBadge = $('#sodar-lz-badge-validate-limit')
  let createBtn = $('#sodar-lz-btn-create-zone')
  let projectLockAlert = $('#sodar-lz-alert-lock')
  let createLimitAlert = $('#sodar-lz-alert-zone-create-limit')
  let validateLimitAlert = $('#sodar-lz-alert-zone-validate-limit')
  $('.sodar-lz-zone-tr-existing').each(function () {
    let trId = $(this).attr('id')
    let zoneTr = $('#' + trId)
    let zoneUuid = $(this).attr('data-zone-uuid')
    let zoneModified = $(this).attr('data-zone-modified')
    let statusTd = zoneTr.find('td#sodar-lz-zone-status-' + zoneUuid)
    if (statusTd.text() !== 'MOVED' && statusTd.text() !== 'DELETED') {
      zoneData[zoneUuid] = {
        'modified': zoneModified
      }
    }
  })
  // Make the POST request to retrieve zone statuses
  $.ajax({
    url: zoneStatusURL,
    method: 'POST',
    dataType: 'JSON',
    contentType: 'application/json',
    data: JSON.stringify({
      zones: zoneData
    }),
  }).done(function (data) {
    let projectLock = data['project_lock']
    let zoneActiveCount = data['zone_active_count']
    let createLimit = data['zone_create_limit']
    let createLimitReached = data['zone_create_limit_reached']
    let zoneValidateCount = data['zone_validate_count']
    let validateLimit = data['zone_validate_limit']
    let validateLimitReached = data['zone_validate_limit_reached']

    // Update create limit badge
    if (createLimit) { // With unlimited creation we don't update this
      createLimitBadge.text(
        zoneActiveCount.toString() + ' / ' + createLimit.toString())
      if (createLimitReached) {
        createLimitBadge.removeClass(
          'badge-success').addClass('badge-warning')
      } else {
        createLimitBadge.removeClass(
          'badge-warning').addClass('badge-success')
      }
    }
    // Update validate limit badge
    validateLimitBadge.text(
      zoneValidateCount.toString() + ' / ' + validateLimit.toString())
    if (validateLimitReached) {
      validateLimitBadge.removeClass(
        'badge-success').addClass('badge-warning')
    } else {
      validateLimitBadge.removeClass(
        'badge-warning').addClass('badge-success')
    }

    // Update project lock alert
    if (projectLock) {
      projectLockAlert.removeClass('d-none').addClass('d-block')
    } else {
      projectLockAlert.removeClass('d-block').addClass('d-none')
    }
    // Update create limit alert
    if (createLimitReached) {
      if (!createBtn.hasClass('disabled')) {
        createBtn.addClass('disabled')
      }
      createLimitAlert.removeClass('d-none').addClass('d-block')
    } else {
      createBtn.removeClass('disabled')
      createLimitAlert.removeClass('d-block').addClass('d-none')
    }
    // Update validate limit alert
    if (validateLimitReached) {
      validateLimitAlert.removeClass('d-none').addClass('d-block')
    } else {
      validateLimitAlert.removeClass('d-block').addClass('d-none')
    }

    // Update individual zones
    $('.sodar-lz-zone-tr-existing').each(function () {
      let zoneUuid = $(this).attr('data-zone-uuid')
      let sampleUrl = $(this).attr('data-sample-url')
      let zoneTr = $('#' + $(this).attr('id'))
      let statusTd = zoneTr.find('td#sodar-lz-zone-status-' +
        zoneUuid)
      let statusInfoSpan = zoneTr.find(
        'span#sodar-lz-zone-status-info-' + zoneUuid)
      let statusStyles = {
        'CREATING': 'bg-warning',
        'NOT CREATED': 'bg-danger',
        'ACTIVE': 'bg-info',
        'PREPARING': 'bg-warning',
        'VALIDATING': 'bg-warning',
        'MOVING': 'bg-warning',
        'MOVED': 'bg-success',
        'FAILED': 'bg-danger',
        'DELETING': 'bg-warning',
        'DELETED': 'bg-secondary'
      }

      if (data.zones[zoneUuid]) {
        let zoneInfo = data.zones[zoneUuid]
        let zoneStatus = zoneInfo.status
        let zoneStatusInfo = zoneInfo.status_info.replaceAll(
          '\n', '<br />')
        let statusInfoHtml = zoneStatusInfo
        if (zoneInfo.truncated) {
          statusInfoHtml +=
            '<span class="sodar-lz-zone-status-truncate">...</span>'
          statusInfoHtml +=
            '<div><a class="sodar-lz-zone-status-link">See more</a></div>'
        }
        // Update data-zone-modified
        zoneTr.attr('data-zone-modified', zoneInfo.modified)
        if (
          statusTd.text() !== zoneStatus ||
          statusInfoSpan.text() !== zoneStatusInfo
        ) {
          statusTd.text(zoneStatus)
          statusTd.removeClass()
          statusTd.addClass(
            'sodar-lz-zone-status ' + statusStyles[zoneStatus] +
            ' text-white')
          statusInfoSpan.html(statusInfoHtml)
          if (['PREPARING', 'VALIDATING', 'MOVING', 'DELETING']
            .includes(zoneStatus)) {
            statusTd.append(
              '<span class="pull-right"><i class="iconify" ' +
              'data-icon="mdi:lock"></i></span>'
            )
          }
          if (['CREATING', 'NOT CREATED', 'MOVED', 'DELETED']
            .includes(zoneStatus)) {
            zoneTr.find('p#sodar-lz-zone-stats-container-' + zoneUuid)
              .hide()
            if (zoneStatus === 'MOVED') {
              let statusMovedSpan = zoneTr.find(
                'span#sodar-lz-zone-status-moved-' + zoneUuid
              )
              statusMovedSpan.html(
                '<p class="sodar-lz-zone-sample-link mb-0">' +
                '<a href="' + sampleUrl + '">' +
                '<i class="iconify" data-icon="mdi:arrow-right-circle"></i> ' +
                'Browse files in sample sheets</a></p>'
              )
            }
          }

          // Button modification
          if (zoneStatus !== 'ACTIVE' &&
            zoneStatus !== 'FAILED' && !isSuperuser) {
            zoneTr.find('.btn').each(function () {
              if ($(this).is('button')) {
                $(this).attr('disabled', 'disabled')
              } else if ($(this).is('a')) {
                $(this).addClass('disabled')
              }
            })
            zoneTr.find('.sodar-list-dropdown').addClass('disabled')
          } else {
            if (zoneStatus !== 'DELETED') {
              zoneTr.find(
                  'p#sodar-lz-zone-stats-container-' + zoneUuid)
                .show()
            }
            zoneTr.find('.btn').each(function () {
              if ($(this).is('button')) {
                $(this).removeAttr('disabled')
              }
              $(this).removeClass('disabled')
            })
            zoneTr.find('.sodar-list-dropdown').removeClass(
              'disabled')
          }
        }
      }

      // Validate/move link modification
      let validateLink = zoneTr.find('.sodar-lz-zone-btn-validate')
      let moveLink = zoneTr.find('.sodar-lz-zone-btn-move')
      // Update validate link
      if (validateLimitReached && !validateLink.hasClass(
          'disabled')) {
        validateLink.addClass('disabled')
      } else if (!validateLimitReached &&
        validateLink.attr('data-can-move') === '1') {
        validateLink.removeClass('disabled')
      }
      // Update move link
      if ((projectLock || validateLimitReached) &&
        !moveLink.hasClass('disabled')) {
        moveLink.addClass('disabled')
      } else if (!projectLock &&
        !validateLimitReached &&
        moveLink.attr('data-can-move') === '1') {
        moveLink.removeClass('disabled')
      }
    })
    window.zoneStatusUpdated = true
  })
}


/**********************
 Modal copy path method
 **********************/
function copyModalPath(path, id) {
  navigator.clipboard.writeText(path)
  displayCopyStatus($('#' + id))
}

/******************
 File list updating
 ******************/
function updateChecksumStatus(checksumUrl, paths) {
  $.ajax({
    url: checksumUrl,
    method: 'POST',
    dataType: 'json',
    contentType: 'application/json',
    data: JSON.stringify({
      'paths': paths
    }),
  }).done(function (data) {
    $('.sodar-lz-obj-list-item-obj').each(function () {
      let path = $(this).attr('data-irods-path')
      if (path in data['checksum_status']) {
        let cell = $(this).find('.sodar-lz-obj-list-item-checksum')
        if (data['checksum_status'][path]) {
          cell.html($('<i>')
            .attr('class', 'iconify text-muted')
            .attr('data-icon', 'mdi:check-bold'))
        } else {
          cell.html($('<i>')
            .attr('class', 'iconify text-danger')
            .attr('data-icon', 'mdi:close-thick'))
        }
      }
    })
  })
}

function updateFileList(
  listUrl, webDavUrl, irodsPathLength, checksumUrl, pageElemId) {
  let tableBody = $('#sodar-lz-obj-table-body')
  let titlePageSpan = $('#sodar-lz-obj-list-title-page')
  if (!listUrl) {
    listUrl = $('#' + pageElemId).attr('data-url')
  }
  // Disable pagination buttons
  $('#sodar-lz-modal-page-item-prev').addClass('disabled')
  $('#sodar-lz-modal-page-item-next').addClass('disabled')

  $.ajax({
      url: listUrl,
      method: 'GET',
      dataType: 'json'
    })
    .done(function (data) {
      // console.log(data); // DEBUG
      let rows = []
      let objPaths = []

      $.each(data['results'], function (i, obj) {
        let objNameSplit = obj['path'].split('/')
        let objPrefix = objNameSplit.slice(
          irodsPathLength, objNameSplit.length - 1).join('/')
        let colSpan = '1'
        let icon = obj['type'] === 'coll' ?
          'mdi:folder-open' :
          'mdi:file-document-outline'
        let toolTip = obj['type'] === 'coll' ? 'Collection' : 'File'
        let elemId = 'sodar-irods-copy-btn-' + i.toString()

        let copyButton = $('<button>')
          .attr('class', 'btn btn-secondary sodar-list-btn pull-right')
          .attr('id', elemId)
          .attr('title', 'Copy iRODS path into clipboard')
          .attr('data-toggle', 'tooltip')
          .attr('data-placement', 'top')
          .click(function () {
            copyModalPath(obj['path'], elemId)
          })
          .append($('<i>')
            .attr('class', 'iconify')
            .attr('data-icon', 'mdi:console-line'))
        let iconHtml = $('<i>')
          .attr('class', 'iconify mr-1')
          .attr('data-icon', icon)
          .attr('title', toolTip)
        let objLink = $('<a>')
          .attr('href', webDavUrl + obj['path'])
        if (objPrefix) {
          objLink.append($('<span>')
            .attr('class', 'text-muted').text(objPrefix + '/'))
        }
        objLink.append(obj['name'])

        let rowClass
        if (obj['type'] === 'obj') rowClass = 'sodar-lz-obj-list-item-obj'
        else rowClass = 'sodar-lz-obj-list-item-coll'

        let row = $('<tr>')
          .attr('class', 'sodar-lz-obj-list-item ' + rowClass)
          .attr('data-irods-path', obj['path'])
          .append($('<td>')
            .attr('colspan', colSpan)
            .append(iconHtml)
            .append(objLink))
        if (obj['type'] === 'obj') {
          row.append($('<td>')
            .text(humanFileSize(obj['size'], true))
          ).append($('<td>')
            .text(obj['modify_time'])
          ).append($('<td>')
            .attr('class', 'sodar-lz-obj-list-item-checksum'))
          // Checksums will be replaced with a separate Ajax call
          objPaths.push(obj['path'])
        } else {
          row.append($('<td>').attr('colspan', '3'))
        }
        row.append($('<td>').append(copyButton))
        // tableBody.append(row)
        rows.push(row)
      })

      if (rows.length > 0) {
        // Update title
        if (data['previous'] || data['next']) {
          // Only update if results need to be paginated
          let titleSuffix = '(' + data['page'] + '/' +
            data['page_count'] + ')'
          titlePageSpan.text(titleSuffix)
        }

        // Display results
        tableBody.html(rows)
        // Update pagination controls
        updatePageConrols(data, webDavUrl, irodsPathLength, checksumUrl)
        // Call for checksum status retrieval
        if (objPaths.length > 0) {
          updateChecksumStatus(checksumUrl, objPaths)
        }
      } else {
        let row = $('<tr>')
          .append($('<td>')
            .attr('colspan', '5')
            .attr('class', 'text-muted font-italic text-center')
            .text('No collections or files in this landing zone.'))
        tableBody.html(row)
      }
    })
}


// Update pagination controls
function updatePageConrols(listData, webDavUrl, irodsPathLength, checksumUrl) {
  let modalPagination = $('#sodar-lz-modal-pagination')
  // If buttons already exist in DOM, simply update
  if (modalPagination.length) {
    let prevBtn = $('#sodar-lz-modal-page-item-prev')
    let prevLink = $('#sodar-lz-modal-link-prev')
    let nextBtn = $('#sodar-lz-modal-page-item-next')
    let nextLink = $('#sodar-lz-modal-link-next')
    if (listData['previous']) {
      prevBtn.removeClass('disabled')
      prevLink.attr('data-url', listData['previous'])
    } else prevBtn.addClass('disabled')
    if (listData['next']) {
      nextBtn.removeClass('disabled')
      nextLink.attr('data-url', listData['next'])
    } else {
      nextBtn.addClass('disabled')
    }
  } else { // Create controls
    let prevClass = 'page-item'
    if (!listData['previous']) prevClass += ' disabled'
    let nextClass = 'page-item'
    if (!listData['next']) nextClass += ' disabled'
    let pageControls = $('<div>')
      .attr('class',
        'pt-3 d-flex justify-content-center sodar-pr-pagination')
      .attr('id', 'sodar-lz-modal-pagination')
      .append($('<ul>')
        .attr('class', 'pagination')
        .append($('<li>')
          .attr('class', prevClass)
          .attr('id', 'sodar-lz-modal-page-item-prev')
          .append($('<a>')
            .attr('class', 'page-link')
            .attr('id', 'sodar-lz-modal-link-prev')
            .attr('data-url', listData['previous'])
            .click(function () {
              updateFileList(
                null,
                webDavUrl,
                irodsPathLength,
                checksumUrl,
                'sodar-lz-modal-link-prev')
            })
            .append($('<i>')
              .attr('class', 'iconify mr-1')
              .attr('data-icon', 'mdi:arrow-left-circle')
            ).append('Prev')))
        .append($('<li>')
          .attr('class', nextClass)
          .attr('id', 'sodar-lz-modal-page-item-next')
          .append($('<a>')
            .attr('class', 'page-link')
            .attr('id', 'sodar-lz-modal-link-next')
            .attr('data-url', listData['next'])
            .click(function () {
              updateFileList(
                null,
                webDavUrl,
                irodsPathLength,
                checksumUrl,
                'sodar-lz-modal-link-next')
            })
            .append('Next')
            .append($('<i>')
              .attr('class', 'iconify ml-1')
              .attr('data-icon', 'mdi:arrow-right-circle')))))
    $('#sodar-lz-obj-pagination').html(pageControls)
  }
}

$(document).ready(function () {
  /*********************
   Get superuser status
   *********************/
  $.when(
    $.ajax({
      url: currentUserURL,
      method: 'GET',
      success: function (response) {
        isSuperuser = response.is_superuser;
      },
      error: function (response) {
        isSuperuser = false;
      }
    })
  ).then(function () {
    /******************
     Update zone status
     ******************/
    updateZoneStatus()
    let statusInterval = window.statusInterval
    // Poll and update active zones
    setInterval(function () {
      updateZoneStatus();
    }, statusInterval)
  })
  // Set up zone UUID copy button
  new ClipboardJS('.sodar-lz-zone-btn-copy')

  // Set up event handling for status info link
  $('body').on('click', 'a.sodar-lz-zone-status-link', function () {
    let zoneUuid = $(this).closest(
      '.sodar-lz-zone-tr').attr('data-zone-uuid')
    $.ajax({
      url: '/landingzones/ajax/status-info/retrieve/' + zoneUuid,
      method: 'GET',
      success: function (response) {
        // console.debug(response.status_info)
        $('#sodar-lz-zone-status-info-' + zoneUuid).html(
          response.status_info.replaceAll('\n', '<br />'))
      }
    })
  })

  // Update collection stats
  updateCollectionStats()
  if ($('table.sodar-lz-table').length === 0) {
    updateButtons();
  }
  let statsSec = 8
  if (typeof (window.irodsbackendStatusInterval) !== 'undefined') {
    statsSec = window.irodsbackendStatusInterval
  }
  let statsInterval = statsSec * 1000
  // Poll and update active collections
  setInterval(function () {
    if ($('table.sodar-lz-table').length === 0) {
      updateButtons();
    }
    updateCollectionStats()
  }, statsInterval)

  // iRODS dir list modal
  $('.sodar-lz-list-modal-btn').click(function () {
    let hashScheme = $('#sodar-lz-zone-list').attr('data-hash-scheme')
    let listUrl = $(this).attr('data-list-url')
    let checksumUrl = $(this).attr('data-checksum-url')
    let irodsPath = $(this).attr('data-irods-path')
    let irodsPathLength = irodsPath.split('/').length
    let webDavUrl = $(this).attr('data-webdav-url')

    let titlePrefix = 'Files in iRODS: ' + irodsPath.split('/').pop()
    let title = $('<span>')
      .attr('id', 'sodar-lz-obj-list-title')
      .text(titlePrefix)
    $('.modal-title').html(title)
      .append($('<span>')
        .attr('id', 'sodar-lz-obj-list-title-page')
        .attr('class', 'ml-1')
      )

    let modalContainer = $('<div>').attr('id',
      'sodar-lz-obj-list-container')
    let table = $('<table>')
      .attr('id', 'sodar-lz-obj-list-table')
      .attr('class', 'table sodar-card-table sodar-irods-obj-table')
      .append($('<thead>')
        .append($('<tr>')
          .append($('<th>').text('File/Collection'))
          .append($('<th>').text('Size'))
          .append($('<th>').text('Modified'))
          .append($('<th>').text(hashScheme.substring(0, 3)))
          .append($('<th>').text('iRODS'))))
      .append($('<tbody>').attr('id', 'sodar-lz-obj-table-body'))
    let pageContainer = $('<div>')
      .attr('id', 'sodar-lz-obj-pagination')
    $('.modal-body').html(
      modalContainer.append(table).append(pageContainer))

    $('#sodar-modal').modal('show')
    updateFileList(listUrl, webDavUrl, irodsPathLength, checksumUrl)
  })
})
