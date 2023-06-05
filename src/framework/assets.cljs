(ns framework.assets
  (:require [clojure.string :as s]
            ["path" :as path]
            ["child_process" :as cp]))

(def basedir (atom "./public"))

(defn set-basedir! [base] (reset! basedir base))

(defn normalize-filename
  [filename basename]
  (cond (and filename (s/includes? filename ".")) filename
        filename (str filename (.extname path basename))
        :else basename))

(defn src->dest
  [{:keys [root dir filename url]}]
  (let [url-obj (js/URL. url)
        url-path (.-pathname url-obj)
        base (normalize-filename filename (.basename path url-path))
        dest-file (.join path root dir base)
        dest-url (.join path dir base)]
    {:url (str "/" dest-url), :filepath dest-file}))

(defn clj->json
  [data]
  (-> data
      (clj->js)
      (js/JSON.stringify)))

(defn download*
  [fields]
  (let [args #js ["./workers/download.cljs" (clj->json fields)]
        opts #js {:encoding "utf-8"}]
    (js/console.log args)
    (.execFile cp "nbb" args opts)))

(defn download
  [dir url & [filename]]
  (if url
    (let [base @basedir
          src {:url url, :root base, :dir dir, :filename filename}
          dest (src->dest src)]
      (download* {:src url, :root base, :dir dir, :dest (:filepath dest)})
      (-> (:url dest)
          (s/trim)))
    ""))
