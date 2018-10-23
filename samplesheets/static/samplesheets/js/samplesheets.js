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
