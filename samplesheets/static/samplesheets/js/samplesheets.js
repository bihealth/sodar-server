$(document).ready(function() {
    /*********************
     Initialize DataTables
     *********************/
    $('.omics-ss-data-table-contentapp').DataTable({
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

    $('.omics-ss-data-table-study').DataTable({
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

    $('.omics-ss-data-table-assay').each(function() {
        var rightCols = 1;

        if ($(this).hasClass('omics-ss-data-hide-links')) {
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
                        'omics-ss-data-cell-links',
                        'omics-ss-data-links-header'],
                    orderable: false
                },
                {
                    targets: 'omics-ss-hideable-study',
                    visible: false
                }
                ],
            dom: 't' // Disable toolbar
        });
    });

    // Once initialized, remove temporary init classes
    $('.omics-ss-init-container').removeClass('table-responsive').removeClass('omics-ss-init-container');

    /*************************
     Enable/disable dragscroll
     *************************/
    $('.omics-ss-data-drag-toggle').click(function() {
        if ($(this).attr('drag-mode') === '0') {
            $(this).find('i').addClass('text-warning');
            $(this).attr('drag-mode', '1');
            $(this).closest('.omics-ss-data-card').find('.dataTables_scrollBody').addClass('dragscroll');
            dragscroll.reset();
        }

        else {
            $(this).find('i').removeClass('text-warning');
            $(this).attr('drag-mode', '0');
            $(this).closest('.omics-ss-data-card').find('.dataTables_scrollBody').removeClass('dragscroll');
            dragscroll.reset();
        }
    });

    /*********
     Filtering
     *********/

    $('.omics-ss-data-filter').keyup(function () {
        var tableId = $(this).closest('.input-group').attr('table-id');
        var dt = $('#' + tableId).dataTable();
        var v = $(this).val();
        dt.fnFilter(v);
    });

    /*******************
     Study column hiding
     *******************/

    // Hide/show study columns when clicked
    $('.omics-ss-assay-hide').click(function () {
        var tableId = $(this).closest('.input-group').attr('table-id');
        var dt = $('#' + tableId).DataTable();

        // Hide
        if ($(this).attr('assay-hide-mode') === '0') {
            $(this).find('i').removeClass('fa-eye').addClass('fa-eye-slash').removeClass('text-warning');
            dt.columns('.omics-ss-hideable-study').visible(false);
            $(this).attr('assay-hide-mode', '1');
        }

        // Show
        else {
            $(this).find('i').removeClass('fa-eye-slash').addClass('fa-eye').addClass('text-warning');
            dt.columns('.omics-ss-hideable-study').visible(true);
            $(this).attr('assay-hide-mode', '0');
        }
    });

    /***************************************
     Disable hover for non-overflowing cells
     ***************************************/

    $('.omics-ss-data-cell-content').each(function() {
        if ($(this).prop('scrollWidth') <= window.maxSheetColumnWidth) {
            $(this).removeClass('omics-ss-overflow');
        }
    });

});
