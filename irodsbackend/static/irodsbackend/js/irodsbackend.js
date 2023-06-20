/***************************************
 Collection statistics updating function
 ***************************************/
var updateCollectionStats = function() {
    var statsPaths = [];
    var projectUUID = null;

    $('span.sodar-irods-stats').each(function () {
        var currentPath = decodeURIComponent($(this).attr(
            'data-stats-url').split('=')[1]);
        if (!projectUUID) {
            projectUUID = currentPath.split('/')[4];
        }
        if (!(statsPaths.includes(currentPath))){
            statsPaths.push(currentPath);
        }
    });

    var d = {paths: statsPaths};

    if (projectUUID) {
        $.ajax({
            url: '/irodsbackend/ajax/stats/' + projectUUID,
            method: 'POST',
            dataType: 'json',
            data: d,
            contentType: "application/x-www-form-urlencoded; charset=UTF-8", //should be default
            traditional: true
        }).done(function (data) {
            $('span.sodar-irods-stats').each(function () {
                var statsSpan = $(this);
                var irodsPath = decodeURIComponent(statsSpan.attr(
                    'data-stats-url')).split('=')[1];
                var fileSuffix = 's';
                for (idx in data['coll_objects']) {
                    if (data['coll_objects'].hasOwnProperty(idx)) {
                        if (irodsPath === data['coll_objects'][idx]['path']
                                && data['coll_objects'][idx]['status'] === '200') {
                            var stats = data['coll_objects'][idx]['stats'];
                            if (stats['file_count'] === 1) {
                                fileSuffix = '';
                            }
                            statsSpan.text(
                                stats['file_count'] + ' file' + fileSuffix +
                                ' ('+ humanFileSize(stats['total_size'], true) + ')');
                            break;
                        }
                    }
                }
            });
        });
    }
};


/***************************************
 Toggling buttons in one row function
 ***************************************/
//enables or disables every .sodar-list-btn button in a row
var toggleButtons = function(row, status, stats) {
    $(row).find('.sodar-list-btn').each(function () {
        if (status === '200') {
            if ($(this).is('button')) {
                $(this).removeAttr('disabled');
            }
            $(this).removeClass('disabled');
            // $(this).tooltip('enable');

            //collection is empty; disable all but the copy path buttons
            if (stats['file_count'] === 0) {
                if ($(this).is('.sodar-irods-popup-list-btn')) {
                    $(this).attr('disabled', 'disabled');
                    // $(this).tooltip('disable');
                } else if ($(this).is('.sodar-irods-dav-btn')) {
                    $(this).addClass('disabled');
                    // $(this).tooltip('disable');
                }
            }
        }
        //collection doesn't exist; disable all buttons
        else {
            if ($(this).is('button')) {
                $(this).attr('disabled', 'disabled');
            } else if ($(this).is('a')) {
                $(this).addClass('disabled');
                $(this).tooltip('disable');
            }
            // $(this).tooltip('disable');
        }
    });
};

/***************************************
 Collection buttons updating function
 ***************************************/
var updateButtons = function() {
    var ipaths = [];
    var projectUUID = '';

    $('button.sodar-irods-path-btn').each(function () {
        if (!$(this).hasClass('no-colls')) {
            var buttonPath = $(this).attr('data-clipboard-text');
            projectUUID = buttonPath.split('/')[4];
            if (!(ipaths.includes(buttonPath))){
                ipaths.push(buttonPath);
            }
        }

        // disable tooltip if dirs are empty
        else {
            $(this).closest('span').find('.sodar-list-btn').each(
                function () {
                    $(this).tooltip('disable');
                });
        }

    });
    var pathCount = ipaths.length;
    var batchSize = window.irodsQueryBatchSize;
    var batchStart = 0;
    var pathBatch = [];

    // Query in batches
    while(batchStart < pathCount) {
        if (pathCount < (batchStart + batchSize)){
            pathBatch = ipaths.slice(batchStart, pathCount);
        } else {
            pathBatch = ipaths.slice(batchStart, batchStart + batchSize);
        }
        batchStart = batchStart+batchSize;
        var d = {paths: pathBatch};

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
                    var buttonPath = $(this).attr('data-clipboard-text');
                    var buttonRow = $(this).closest('span');
                    for (idx in data['coll_objects']) {
                        if (data['coll_objects'].hasOwnProperty(idx)) {
                            if (buttonPath === data['coll_objects'][idx]['path']) {
                                var status = data['coll_objects'][idx]['status'];
                                var stats = data['coll_objects'][idx]['stats'];
                                toggleButtons(buttonRow, status, stats);
                                break;
                            }
                        }
                    }
                });
            });
        }
    }
};


/******************
 Copy path function
 ******************/
function copy_path(path, id) {
    // Copy the text inside the text field
    navigator.clipboard.writeText(path);

    // Note of copy
    var elem = $('#' + id);
    elem.addClass('text-warning');
    if (elem.attr('data-table') !== '1') {
        var realTitle = elem.tooltip().attr('data-original-title');
        elem.attr('title', 'Copied!')
            .tooltip('_fixTitle')
            .tooltip('show')
            .attr('title', realTitle)
            .tooltip('_fixTitle');
    }
    elem.delay(250).queue(function() {
        elem.removeClass('text-warning').dequeue();
    });
}


$(document).ready(function() {
    /***************
     Init Clipboards
     ***************/
    new ClipboardJS('.sodar-irods-copy-btn');

    /******************
     Copy link handling
     ******************/
    $('.sodar-irods-copy-btn').click(function () {
        $(this).addClass('text-warning');
        if ($(this).attr('data-table') !== '1') {
            var realTitle = $(this).tooltip().attr('data-original-title');
            $(this).attr('title', 'Copied!')
                .tooltip('_fixTitle')
                .tooltip('show')
                .attr('title', realTitle)
                .tooltip('_fixTitle');
        }
        $(this).delay(250).queue(function() {
            $(this).removeClass('text-warning').dequeue();
        });
    });

    /***********************
     Update collection stats
     ***********************/
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

    /***************
     Link list Popup
     ***************/
    $('.sodar-irods-popup-list-btn').click(function() {
        var listUrl = $(this).attr('data-list-url');
        var irodsPath = $(this).attr('data-irods-path');
        var irodsPathLength = irodsPath.split('/').length;
        var webDavUrl = $(this).attr('data-webdav-url');
        var body = '';
        var showChecksumCol = false;
        if (typeof(window.irodsShowChecksumCol) !== 'undefined') {
            showChecksumCol = window.irodsShowChecksumCol;
        }

        $('.modal-title').text('Files in iRODS: ' + irodsPath.split('/').pop());

        $.ajax({
                url: listUrl,
                method: 'GET',
                dataType: 'json'
            }).done(function (data) {
            // console.log(data); // DEBUG

            if (data['irods_data'].length > 0) {
                body += '<table class="table sodar-card-table sodar-irods-obj-table">';
                body += '<thead><th>File/Collection</th><th>Size</th><th>Modified</th>';
                if (showChecksumCol === true) {
                    body += '<th>MD5</th>';
                }
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

                    var colSpan = obj['type'] === 'coll' ? '1' : '4';
                    var icon = obj['type'] === 'coll' ? 'mdi:folder-open' : 'mdi:file-document-outline';
                    var toolTip = obj['type'] === 'coll' ? 'Collection' : 'File';

                    var copyButton = '';
                    if (obj['type'] === 'coll') {
                        copyButton = '<button class="btn btn-secondary sodar-list-btn pull-right" ' +
                            'id="sodar-irods-copy-btn-' + obj['name'] + '" ' +
                            'title="Copy iRODS path into clipboard" data-tooltip="tooltip" ' +
                            'data-placement="top" onclick="copy_path(\'' + obj['path'] + '\', \'sodar-irods-copy-btn-' + obj['name'] + '\')">' +
                            '<i class="iconify" data-icon="mdi:clipboard-text-multiple"></i>' +
                            '</button>';
                    }

                    var iconHtml = '<i class="iconify mr-1" data-icon="' + icon + '"' +
                        ' title="' + toolTip + '"></i>';
                    body += '<tr><td colspan="' + colSpan + '">' + iconHtml + objLink + copyButton + '</td>';

                    if (obj['type'] === 'obj') {
                        body += '<td>' + humanFileSize(obj['size'], true) + '</td>';
                        body += '<td>' + obj['modify_time'] + '</td><td>';
                        if (showChecksumCol === true) {
                            if (obj['md5_file'] === true) {
                                body += '<span class="text-muted">' +
                                    '<i class="iconify" data-icon="mdi:check-bold"></i></span>';
                            } else {
                                body += '<span class="text-danger">' +
                                    '<i class="iconify" data-icon="mdi:close-thick"></i></span>';
                            }
                        }
                        body += '</td>';
                    }
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
