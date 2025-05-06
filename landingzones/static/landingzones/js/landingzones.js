// Init global variable
var isSuperuser = false;

/*********************
 Zone status updating
 *********************/
var updateZoneStatus = function() {
    window.zoneStatusUpdated = false;
    var zoneData = {};
    $('.sodar-lz-zone-tr-existing').each(function() {
        var trId = $(this).attr('id');
        var zoneTr = $('#' + trId);
        var zoneUuid = $(this).attr('data-zone-uuid');
        var zoneModified = $(this).attr('data-zone-modified');
        var statusTd = zoneTr.find('td#sodar-lz-zone-status-' + zoneUuid);
        if (statusTd.text() !== 'MOVED' && statusTd.text() !== 'DELETED') {
            zoneData[zoneUuid] = {'modified': zoneModified}
        }
    });
    // Make the POST request to retrieve zone statuses
    if (Object.keys(zoneData).length > 0) {
        $.ajax({
            url: zoneStatusURL,
            method: 'POST',
            dataType: 'JSON',
            contentType: 'application/json',
            data: JSON.stringify({zones: zoneData}),
        }).done(function(data) {
            $('.sodar-lz-zone-tr-existing').each(function() {
                var zoneUuid = $(this).attr('data-zone-uuid');
                var sampleUrl = $(this).attr('data-sample-url');
                var zoneTr = $('#' + $(this).attr('id'));
                var statusTd = zoneTr.find('td#sodar-lz-zone-status-' + zoneUuid);
                var statusInfoSpan = zoneTr.find(
                    'span#sodar-lz-zone-status-info-' + zoneUuid);
                var statusStyles = {
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
                };
                if (data[zoneUuid]) {
                    var zoneStatus = data[zoneUuid].status;
                    var zoneStatusInfo = data[zoneUuid].status_info.replaceAll(
                        '\n', '<br />');
                    var statusInfoHtml = zoneStatusInfo;
                    if (data[zoneUuid].truncated) {
                        statusInfoHtml += '<span class="sodar-lz-zone-status-truncate">...</span>';
                        statusInfoHtml += '<div><a class="sodar-lz-zone-status-link">See more</a></div>';
                    }
                    // Update data-zone-modified
                    zoneTr.attr('data-zone-modified', data[zoneUuid].modified);
                    if (
                        statusTd.text() !== zoneStatus ||
                        statusInfoSpan.text() !== zoneStatusInfo
                    ) {
                        statusTd.text(zoneStatus);
                        statusTd.removeClass();
                        statusTd.addClass(
                            'sodar-lz-zone-status ' + statusStyles[zoneStatus] + ' text-white');
                        statusInfoSpan.html(statusInfoHtml);
                        if (['PREPARING', 'VALIDATING', 'MOVING', 'DELETING'].includes(zoneStatus)) {
                            statusTd.append(
                                '<span class="pull-right"><i class="iconify" data-icon="mdi:lock"></i></span>'
                            );
                        }
                        if (['CREATING', 'NOT CREATED', 'MOVED', 'DELETED'].includes(zoneStatus)) {
                            zoneTr.find('p#sodar-lz-zone-stats-container-' + zoneUuid).hide();
                            if (zoneStatus === 'MOVED') {
                                var statusMovedSpan = zoneTr.find(
                                    'span#sodar-lz-zone-status-moved-' + zoneUuid
                                );
                                statusMovedSpan.html(
                                    '<p class="sodar-lz-zone-sample-link mb-0">' +
                                    '<a href="' + sampleUrl + '">' +
                                    '<i class="iconify" data-icon="mdi:arrow-right-circle"></i> ' +
                                    'Browse files in sample sheets</a></p>'
                                );
                            }
                        }

                        // Button modification
                        if (zoneStatus !== 'ACTIVE' && zoneStatus !== 'FAILED' && !isSuperuser) {
                            zoneTr.find('.btn').each(function() {
                                if ($(this).is('button')) {
                                    $(this).attr('disabled', 'disabled');
                                } else if ($(this).is('a')) {
                                    $(this).addClass('disabled');
                                }
                            });
                            zoneTr.find('.sodar-list-dropdown').addClass('disabled');
                        } else {
                            if (zoneStatus !== 'DELETED') {
                                zoneTr.find('p#sodar-lz-zone-stats-container-' + zoneUuid).show();
                            }
                            zoneTr.find('.btn').each(function() {
                                if ($(this).is('button')) {
                                    $(this).removeAttr('disabled');
                                }
                                $(this).removeClass('disabled');
                            });
                            zoneTr.find('.sodar-list-dropdown').removeClass('disabled');
                        }
                    }
                }
            });
        window.zoneStatusUpdated = true;
        });
    }
};


/*****************************
 Project lock status updating
 *****************************/
var updateLockStatus = function() {
    var lockAlert = $('#sodar-lz-alert-lock');
    var lockUrl = lockAlert.attr('data-lock-url');
    $.ajax({
        url: lockUrl,
        method: 'GET',
    }).done(function(data) {
        if (data.is_locked) {
            lockAlert.removeClass('d-none').addClass('d-block');
            $('.sodar-lz-zone-btn-process').each(function() {
                if (!$(this).hasClass('disabled')) {
                    $(this).addClass('disabled');
                }
            });
        } else if (!data.is_locked) {
            lockAlert.removeClass('d-block').addClass('d-none');
            $('.sodar-lz-zone-btn-process').each(function() {
                if ($(this).getAttribute('data-can-move') === '1') {
                    $(this).removeClass('disabled');
                }
            });
        }
    });
}

/**********************
 Modal copy path method
 **********************/
function copyModalPath(path, id) {
    navigator.clipboard.writeText(path);
    displayCopyStatus($('#' + id));
}

$(document).ready(function() {
    /*********************
     Get superuser status
     *********************/
    $.when(
        $.ajax({
            url: currentUserURL,
            method: 'GET',
            success: function(response) {
                isSuperuser = response.is_superuser;
            },
            error: function(response) {
                isSuperuser = false;
            }
        })
    ).then(function() {
        /******************
         Update zone status
         ******************/
        updateZoneStatus();
        var statusInterval = window.statusInterval;
        // Poll and update active zones
        setInterval(function() {
            updateZoneStatus();
        }, statusInterval);
    });
    // Set up zone UUID copy button
    new ClipboardJS('.sodar-lz-zone-btn-copy');

    // Set up event handling for status info link
    $('body').on('click', 'a.sodar-lz-zone-status-link', function () {
        var zoneUuid = $(this).closest(
            '.sodar-lz-zone-tr').attr('data-zone-uuid');
        $.ajax({
            url: '/landingzones/ajax/status-info/retrieve/' + zoneUuid,
            method: 'GET',
            success: function(response) {
                // console.debug(response.status_info);
                $('#sodar-lz-zone-status-info-' + zoneUuid).html(
                    response.status_info.replaceAll('\n', '<br />'));
            }
        });
    });

    // Update collection stats
    updateCollectionStats();
    if ($('table.sodar-lz-table').length === 0) {
        updateButtons();
    }
    var statsSec = 8;
    if (typeof(window.irodsbackendStatusInterval) !== 'undefined') {
        statsSec = window.irodsbackendStatusInterval;
    }
    var statsInterval = statsSec * 1000;
    // Poll and update active collections
    setInterval(function () {
        if ($('table.sodar-lz-table').length === 0) {
            updateButtons();
        }
        updateCollectionStats();
    }, statsInterval);

    // Poll and update project lock status
    updateLockStatus();
    var lockInterval = 5000;
    setInterval(function() {
        updateLockStatus();
    }, lockInterval)

    // iRODS dir list modal
    $('.sodar-lz-list-modal-btn').click(function() {
        var listUrl = $(this).attr('data-list-url');
        var irodsPath = $(this).attr('data-irods-path');
        var irodsPathLength = irodsPath.split('/').length;
        var webDavUrl = $(this).attr('data-webdav-url');
        var body = '';
        $('.modal-title').text('Files in iRODS: ' + irodsPath.split('/').pop());

        $.ajax({url: listUrl, method: 'GET', dataType: 'json'}).done(function (data) {
            // console.log(data); // DEBUG
            if (data['irods_data'].length > 0) {
                body += '<table class="table sodar-card-table sodar-irods-obj-table">';
                body += '<thead><th>File/Collection</th><th>Size</th><th>Modified</th>';
                body += '<th>MD5</th><th>iRODS</th>';
                body += '</thead><tbody>';

                $.each(data['irods_data'], function (i, obj) {
                    var objNameSplit = obj['path'].split('/');
                    var objPrefix = objNameSplit.slice(
                        irodsPathLength, objNameSplit.length - 1).join('/');
                    var objLink = '<a href="' + webDavUrl + obj['path'] + '">';
                    if (objPrefix) {
                        objLink += '<span class="text-muted">' + objPrefix + '/</span>';
                    }
                    objLink += obj['name'] + '</a>';

                    var colSpan = '1';
                    var icon = obj['type'] === 'coll' ? 'mdi:folder-open' : 'mdi:file-document-outline';
                    var toolTip = obj['type'] === 'coll' ? 'Collection' : 'File';
                    var elemId = 'sodar-irods-copy-btn-' + i.toString();
                    var copyButton = '<button class="btn btn-secondary sodar-list-btn pull-right" ' +
                        'id="' + elemId + '"' +
                        'title="Copy iRODS path into clipboard" ' +
                        'data-placement="top" onclick="copyModalPath(\'' + obj['path'] +
                        '\', \'' + elemId + '\')">' +
                        '<i class="iconify" data-icon="mdi:console-line"></i>' +
                        '</button>';
                    var iconHtml = '<i class="iconify mr-1" data-icon="' + icon + '"' +
                        ' title="' + toolTip + '"></i>';
                    body += '<tr><td colspan="' + colSpan + '">' + iconHtml + objLink + '</td>';

                    if (obj['type'] === 'obj') {
                        body += '<td>' + humanFileSize(obj['size'], true) + '</td>';
                        body += '<td>' + obj['modify_time'] + '</td><td>';
                        if (obj['md5_file'] === true) {
                            body += '<span class="text-muted">' +
                                '<i class="iconify" data-icon="mdi:check-bold"></i></span>';
                        } else {
                            body += '<span class="text-danger">' +
                                '<i class="iconify" data-icon="mdi:close-thick"></i></span>';
                        }
                        body += '</td>';
                    } else {
                        body += '<td colspan="3"></td>';
                    }
                    body += '<td>' + copyButton + '</td>';
                    body += '</tr>';
                });
            } else {
                body += '<span class="text-muted font-italic">No files</span>';
            }

            // Set success content and toggle modal
            $('.modal-body').html(body);
            $('#sodar-modal-wait').modal('hide');
            $('#sodar-modal').modal('show');
        }).fail(function (response) {
            // Set failure content and toggle modal
            if (response.status === 404) {
                $('.modal-body').html(
                    '<span class="text-muted font-italic">Collection not found</span>');
            } else {
                $('.modal-body').html(
                    '<span class="text-danger font-italic">Failed to query data (' +
                    response.status + ': ' + response.responseText + ')</span>');
            }
            $('#sodar-modal-wait').modal('hide');
            $('#sodar-modal').modal('show');
        });
        // Set waiting content and toggle modal
        $('#sodar-modal-wait').modal('show');
    });
});
