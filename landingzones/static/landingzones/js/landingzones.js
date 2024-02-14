// Init global variable
var isSuperuser = false;

/*****************************
 Zone status updating function
 *****************************/
var updateZoneStatus = function() {
    window.zoneStatusUpdated = false;
    var zoneUuids = [];
    $('.sodar-lz-zone-tr-existing').each(function() {
        var trId = $(this).attr('id');
        var zoneTr = $('#' + trId);
        var zoneUuid = $(this).attr('data-zone-uuid');
        var statusTd = zoneTr.find('td#sodar-lz-zone-status-' + zoneUuid);

        if (statusTd.text() !== 'MOVED' && statusTd.text() !== 'DELETED') {
            zoneUuids.push(zoneUuid);
        }
    });
    // Make the POST request to retrieve zone statuses
    if (zoneUuids.length > 0) {
        $.ajax({
            url: zoneStatusURL,
            method: 'POST',
            dataType: 'JSON',
            data: {zone_uuids: zoneUuids}
        }).done(function(data) {
            $('.sodar-lz-zone-tr-existing').each(function() {
                var zoneUuid = $(this).attr('data-zone-uuid');
                var zoneTr = $('#' + $(this).attr('id'));
                var statusTd = zoneTr.find('td#sodar-lz-zone-status-' + zoneUuid);
                var statusInfoSpan = zoneTr.find('span#sodar-lz-zone-status-info-' + zoneUuid);
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
                    var zoneStatusInfo = data[zoneUuid].status_info;
                    if (
                        statusTd.text() !== zoneStatus ||
                        statusInfoSpan.text() !== zoneStatusInfo
                    ) {
                        statusTd.text(zoneStatus);
                        statusTd.removeClass();
                        statusTd.addClass(statusStyles[zoneStatus] + ' text-white');
                        statusInfoSpan.text(zoneStatusInfo);
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
                                    '<p class="mb-0"><a href="' + sampleUrl + '">' +
                                    '<i class="iconify" data-icon="mdi:arrow-right-circle"></i> ' +
                                    'Browse files in sample sheet</a></p>'
                                );
                            }
                        }

                        // Button modification
                        if (zoneStatus !== 'ACTIVE' && zoneStatus !== 'FAILED' && !isSuperuser) {
                            zoneTr.find('td.sodar-lz-zone-title').addClass('text-muted');
                            zoneTr.find('td.sodar-lz-zone-assay').addClass('text-muted');
                            zoneTr.find('td.sodar-lz-zone-status-info').addClass('text-muted');
                            zoneTr.find('.btn').each(function() {
                                if ($(this).is('button')) {
                                    $(this).attr('disabled', 'disabled');
                                } else if ($(this).is('a')) {
                                    $(this).addClass('disabled');
                                }
                                $(this).tooltip('disable');
                            });
                            zoneTr.find('.sodar-list-dropdown').addClass('disabled');
                        } else {
                            zoneTr.find('td.sodar-lz-zone-title').removeClass('text-muted');
                            zoneTr.find('td.sodar-lz-zone-assay').removeClass('text-muted');
                            zoneTr.find('td.sodar-lz-zone-status-info').removeClass('text-muted');
                            if (zoneStatus !== 'DELETED') {
                                zoneTr.find('p#sodar-lz-zone-stats-container-' + zoneUuid).show();
                            }
                            zoneTr.find('.btn').each(function() {
                                if ($(this).is('button')) {
                                    $(this).removeAttr('disabled');
                                }
                                $(this).removeClass('disabled');
                                $(this).tooltip('enable');
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
});
