/********************************
 Enable/disable shortcut buttons
 ********************************/
async function toggleShortcuts (table){
    var filePaths = [];

    //get study UUID
    studyID = $('.sodar-ss-nav-btn.active').attr('href').split('/').pop();

    // HACK to check if 'study' is already in the url
    var study = 'study/';
    if (window.location.pathname.includes('/study/')) {
        study = '';
    }
    var url = study + 'germline/filecheck';

    // get all the button paths to query all at once
    table.find('a.sodar-list-btn').not('.sodar-igv-btn').each(function (){
        var path = $(this).attr('href');
        if(! filePaths.includes(path)){
            filePaths.push(path);
        }
    });

    if (table.attr('id').includes('cancer')){
        url = study + 'cancer/filecheck';
    }

    var pathCount = filePaths.length;
    var batchSize = window.queryBatchSize;
    var batchStart = 0;
    var pathBatch = [];

    // Query in batches
    while(batchStart < pathCount) {
        if (pathCount < (batchStart + batchSize)){
            pathBatch = filePaths.slice(batchStart, pathCount);
        }
        else {
            pathBatch = filePaths.slice(batchStart, batchStart + batchSize);
        }
        batchStart = batchStart + batchSize;
        var d = {paths: pathBatch};

        // Check if files exist and enable the corresponding buttons
        $.ajax({
            url: url + '/' + studyID,
            method: 'POST',
            data: d,
            traditional: true
        }).done(function (data) {
            table.find('tr').each(function () {
                var buttonRow = $(this);
                var igvEnable = false;
                $(this).find('a.sodar-list-btn').each(function () {
                    var buttonPath = $(this).attr('href');
                    for (idx in data['files']) {
                        if (data['files'].hasOwnProperty(idx)) {
                            if (buttonPath === data['files'][idx]['path']) {
                                if (data['files'][idx]['exists']) {
                                    $(this).removeClass('disabled');
                                    $(this).tooltip('enable');
                                    igvEnable = true;
                                } else {
                                    $(this).addClass('disabled');
                                    $(this).tooltip('disable');
                                }
                                break;
                            }
                        }
                    }
                });

                // Toggle IGV buttons
                buttonRow.find('.sodar-igv-btn').each(function () {
                    if (igvEnable) {
                        if ($(this).is('button')) {
                            $(this).removeAttr('disabled');
                        } else if ($(this).is('a')) {
                            $(this).removeClass('disabled');
                        }
                        $(this).tooltip('enable');
                    } else {
                        if ($(this).is('button')) {
                            $(this).attr('disabled', 'disabled');
                        } else if ($(this).is('a')) {
                            $(this).addClass('disabled');
                        }
                        $(this).tooltip('disable');
                    }
                });
            });


        });
    }
};


$(document).ready(function() {

    /*********************
     Initialize DataTables
     *********************/
    $('.sodar-ss-data-table-contentapp').DataTable({
        scrollY: 300,
        scrollX: true,
        paging: false,
        scrollCollapse: true,
        info: false,
        fixedColumns: {
            leftColumns: 0,
            rightColumns: 0
        },
        dom: 't' // Disable toolbar
    });

    $('.sodar-ss-data-table-study').DataTable({
        scrollY: 300,
        scrollX: true,
        paging: false,
        scrollCollapse: true,
        info: false,
        fixedColumns: {
            leftColumns: 0,
            rightColumns: 0
        },
        dom: 't' // Disable toolbar
    });

    $('.sodar-ss-data-table-assay').each(function() {
        var rightCols = 1;

        if ($(this).hasClass('sodar-ss-data-hide-links')) {
            rightCols = 0;
        }

        $(this).DataTable({
            scrollY: 400,
            scrollX: true,
            paging: false,
            scrollCollapse: true,
            info: false,
            fixedColumns: {
                leftColumns: 0,
                rightColumns: rightCols
            },
            columnDefs: [
                {
                    // Disable sorting from links column
                    targets: [
                        'sodar-ss-data-cell-links',
                        'sodar-ss-data-links-header'],
                    orderable: false
                },
                {
                    targets: 'sodar-ss-hideable-study',
                    visible: false
                }
                ],
            dom: 't' // Disable toolbar
        });
    });

    // Once initialized, remove temporary init classes
    $('.sodar-ss-init-container').removeClass('table-responsive').removeClass('sodar-ss-init-container');

    // Enable/Disable shortcut buttons
    // NOTE: Currently limiting to study apps (see issue #428)
    $('table.sodar-ss-data-table-studyapp').each(function() {
        if (this.hasAttribute('id')){
            toggleShortcuts($(this));
        }
    });

    /*************************
     Enable/disable dragscroll
     *************************/
    $('.sodar-ss-data-drag-toggle').click(function() {
        if ($(this).attr('drag-mode') === '0') {
            $(this).find('i').addClass('text-warning');
            $(this).attr('drag-mode', '1');
            $(this).closest('.sodar-ss-data-card').find('.dataTables_scrollBody').addClass('dragscroll');
            dragscroll.reset();
        }

        else {
            $(this).find('i').removeClass('text-warning');
            $(this).attr('drag-mode', '0');
            $(this).closest('.sodar-ss-data-card').find('.dataTables_scrollBody').removeClass('dragscroll');
            dragscroll.reset();
        }
    });

    /*********
     Filtering
     *********/

    $('.sodar-ss-data-filter').keyup(function () {
        var tableId = $(this).closest('.input-group').attr('table-id');
        var dt = $('#' + tableId).dataTable();
        var v = $(this).val();
        dt.fnFilter(v);
    });

    /*******************
     Study column hiding
     *******************/

    // Hide/show study columns when clicked
    $('.sodar-ss-assay-hide').click(function () {
        var tableId = $(this).closest('.input-group').attr('table-id');
        var dt = $('#' + tableId).DataTable();

        // Hide
        if ($(this).attr('assay-hide-mode') === '0') {
            $(this).find('i').removeClass('fa-eye').addClass('fa-eye-slash').removeClass('text-warning');
            dt.columns('.sodar-ss-hideable-study').visible(false);
            $(this).attr('assay-hide-mode', '1');
        }

        // Show
        else {
            $(this).find('i').removeClass('fa-eye-slash').addClass('fa-eye').addClass('text-warning');
            dt.columns('.sodar-ss-hideable-study').visible(true);
            $(this).attr('assay-hide-mode', '0');
        }
    });
});
