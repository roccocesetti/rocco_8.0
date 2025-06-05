$(
    function () {
        var ck = false;
        if ( document.cookie && document.cookie.match(/cookie=1/) ) {
            ck = true;
        }
         
        if ( ! ck ) {
            $("body").append(
                "<section id='cookie'>\
                    Questo sito utilizza cookie tecnici per offrirti una migliore esperienza di navigazione sul sito. Se vuoi saperne di più premi\
                    <a href='https://www.ideawork.link/blog/comunicazione-aziendale-novita-uscita-nuovi-moduli-software-1/post/cookie-garante-della-privacy-34389#'>questo link</a> oppure \
                    <a href='#' data-show='none' data-setc='closecookie'>Chiudi</a> questo avviso.\
                </section>"
            );
             
            $("#cookie").css({
                position: "fixed"
                , top: 0
                , left: 0
                , width: "100%"
                , background: "rgba(254,203,0,0.8)"
                , "z-index": 60
                , padding: "1em"
                , color: "#000055"
                , "text-align": "center"
                , "box-shadow": "0 .5em .5em rgba(0,0,0,.5)"
                , margin: 0
                , "min-height": 0
            });
             
            $("#cookie>a").css({
                "text-decoration": "none"
                , width: "8em"
                , background: "#0099ff"
                , color: "#fff"
                , "border-radius": ".2em"
                , display: "inline-block"
                , "text-align": "center"
            });
             
            $("#cookie>a:first").css({
                background: "#ff7d00"
            });
             
            $("a[data-setc='closecookie']").click(
                function (e) {
                    $("#cookie").remove();
                    document.cookie = [
                        encodeURIComponent('cookie'), '=1',
                        '; expires=Sat, 31 Dec 2050 00:00:00 UTC',
                        '; path=/'
                    ].join('');
                }
            );
        }
    }
);
