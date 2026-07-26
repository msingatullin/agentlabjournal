(function(m,e,t,r,i,k,a){
    m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
    m[i].l=1*new Date();
    for (var j=0; j<document.scripts.length; j++) { if (document.scripts[j].src === r) return; }
    k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
})(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js?id=110942679', 'ym');
ym(110942679, 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:'dataLayer', referrer:document.referrer, url:location.href, accurateTrackBounce:true, trackLinks:true});

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('audio[data-podcast-id]').forEach(function (audio) {
        var sent = {};
        var params = {
            episode: audio.dataset.podcastId,
            language: audio.dataset.podcastLanguage || document.documentElement.lang || 'unknown'
        };
        function reachGoal(name) {
            if (sent[name]) return;
            sent[name] = true;
            ym(110942679, 'reachGoal', name, params);
        }
        audio.addEventListener('play', function () {
            reachGoal('podcast_play');
        });
        audio.addEventListener('timeupdate', function () {
            if (Number.isFinite(audio.duration) && audio.duration > 0 && audio.currentTime / audio.duration >= 0.25) {
                reachGoal('podcast_25');
            }
        });
        audio.addEventListener('ended', function () {
            reachGoal('podcast_complete');
        });
    });
});
