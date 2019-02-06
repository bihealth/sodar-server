/***************************************
 Collection statistics updating function
 ***************************************/
var updateCollectionStats = function() {
    var statsPaths = [];
    var projectUUID = '';

    $('span.sodar-irods-stats').each(function () {
        var statsUrl = ($(this).attr('stats-url')).split('=')[1];
        projectUUID = statsUrl.split('/')[4];

        if (!(statsPaths.includes(statsUrl))){
            statsPaths.push(statsUrl);
        }
    });
    var d = {paths: statsPaths};

    if (projectUUID !== '') {
        $.ajax({
            url: '/irodsbackend/api/stats/' + projectUUID,
            method: 'POST',
            dataType: 'json',
            data: d,
            contentType: "application/x-www-form-urlencoded; charset=UTF-8", //should be default
            traditional: true
        }).done(function (data) {
            $('span.sodar-irods-stats').each(function () {
                var statsSpan = $(this);
                var statsUrl = (statsSpan.attr('stats-url')).split('=')[1];
                var fileSuffix = 's';
                for (idx in data['coll_objects']) {
                    if (data['coll_objects'].hasOwnProperty(idx)) {
                        if (statsUrl === data['coll_objects'][idx]['path']
                                && data['coll_objects'][idx]['status'] === '200') {
                            var stats = data['coll_objects'][idx]['stats'];
                            if (stats['file_count'] === 1) {
                                fileSuffix = '';
                            }
                            statsSpan.text(
                                stats['file_count'] + ' data file' + fileSuffix +
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
            $(this).tooltip('enable');

            //collection is empty; disable all but the copy path buttons
            if(stats['file_count'] === 0){
                if ($(this).is('.sodar-irods-popup-list-btn')) {
                    $(this).attr('disabled', 'disabled');
                    $(this).tooltip('disable');
                }
                else if ($(this).is('.sodar-irods-dav-btn')){
                    $(this).addClass('disabled');
                    $(this).tooltip('disable');
                }
            }
        }
        //collection doesn't exist; disable all buttons
        else{
            if ($(this).is('button')) {
                $(this).attr('disabled', 'disabled');
            } else if ($(this).is('a')) {
                $(this).addClass('disabled');
            }
            $(this).tooltip('disable');
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
        var buttonPath = $(this).attr('data-clipboard-text');
        projectUUID = buttonPath.split('/')[4];
        if (!(ipaths.includes(buttonPath))){
            ipaths.push(buttonPath);
        }
    });
    var d = {paths: ipaths};

    if (projectUUID !== '') {
        $.ajax({
            url: '/irodsbackend/api/stats/' + projectUUID,
            method: 'POST',
            dataType: 'json',
            data: d,
            contentType: "application/x-www-form-urlencoded; charset=UTF-8", //should be default
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
};



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
        var listUrl = $(this).attr('list-url');
        var irodsPath = $(this).attr('irods-path');
        var irodsPathLength = irodsPath.split('/').length;
        var webDavUrl = $(this).attr('webdav-url');
        var htmlData = '';
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
            // console.log(data);  // DEBUG

            if (data['data_objects'].length > 0) {
                htmlData += '<table class="table sodar-card-table table-striped sodar-irods-obj-table">';
                htmlData += '<thead><th>File</th><th>Size</th><th>Modified</th>';

                if (showChecksumCol === true) {
                    htmlData += '<th>MD5</th>';
                }

                htmlData += '</thead><tbody>';

                $.each(data['data_objects'], function (i, obj) {
                    var objNameSplit = obj['path'].split('/');
                    var objLink = '<a href="' + webDavUrl + obj['path'] + '"><span class="text-muted">';
                    objLink += objNameSplit.slice(irodsPathLength, objNameSplit.length - 1).join('/');
                    objLink += '/</span>' + obj['name'] + '</a>';
                    htmlData += '<tr><td>' + objLink + '</td>';
                    htmlData += '<td>' + humanFileSize(obj['size'], true) + '</td>';
                    htmlData += '<td>' + obj['modify_time'] + '</td>';
                    htmlData += '<td>';

                    if (showChecksumCol === true) {
                        if (obj['md5_file'] === true) {
                            htmlData += '<span class="text-muted"><i class="fa fa-check"></i></span>';
                        }

                        else {
                            htmlData += '<span class="text-danger"><i class="fa fa-close"></i></span>';
                        }
                    }

                    htmlData += '</td></tr>';
                });
            }

            else {
                htmlData += '<span class="text-muted font-italic">Empty collection</span>';
            }

            // Set success content and toggle modal
            $('.modal-body').html(htmlData);
            $('#sodar-modal-wait').modal('hide');
            $('#sodar-modal').modal('show');
        }).fail(function (response) {
            // Set failure content and toggle modal
            if (response.status === 404) {
                $('.modal-body').html(
                    '<span class="text-muted font-italic">Collection not found</span>');
            }

            else {
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
