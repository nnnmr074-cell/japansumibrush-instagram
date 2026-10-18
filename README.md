# japansumibrush-instagram

Media and scheduler for [@japansumibrush](https://www.instagram.com/japansumibrush/) — Japanese ink-wash style art prints, available on [Etsy](https://www.etsy.com/shop/JapanSumiBrush).

- `media/` — web-size images and videos used in Instagram posts (not the print files).
- `queue/posts.json` — the posting schedule. Only posts marked `approved` are published.
- `.github/workflows/post.yml` — checks every hour and publishes posts whose time has come.
- `.github/workflows/refresh-token.yml` — keeps the Instagram access token valid.

© JapanSumiBrush. All artwork is copyrighted; please do not reuse.
