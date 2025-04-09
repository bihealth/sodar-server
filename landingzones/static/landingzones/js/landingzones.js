// Init global variable
var isSuperuser = false;

/*****************************
 Zone status updating function
 *****************************/
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
});
