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
                var sampleUrl = $(this).attr('data-sample-url');
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
                        statusTd.addClass(
                            'sodar-lz-zone-status ' + statusStyles[zoneStatus] + ' text-white');
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
});
