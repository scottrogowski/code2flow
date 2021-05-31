var g = (function() {
    function a() {
        function c() {
            function d() {
                console.log('d');
            }
            d()
        }
        b();
        c();
    }

    function b() {
        console.log("c");
    }

    return {
        'a': a,
        'b': b
        }
})()
