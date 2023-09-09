(ns framework.assets
  (:require
    [promesa.core :as p]
    [gracie.queue :as q]
    ["path" :as path]
    ["stream" :refer [Readable]]
    ["stream/promises" :refer [pipeline]]
    ["fs" :as fs]
    ["fs/promises" :as fsp]))

(defn url->path
  [url-str]
  (let [url (js/URL. url-str)]
   (.-pathname url)))

(defn fetch-download
  [url target-dir file-path]
  (p/let [response (js/fetch url)]
    (p/do
      (fsp/mkdir target-dir #js {:recursive true})
      (pipeline
        (.fromWeb Readable (.-body response))
        (fs/createWriteStream file-path)))))

(defn enqueue-download
  [url target-dir file-path]
  (q/enqueue
    {:type :resource
     :requests [{:id (url->path url)
                 :fetch #(fetch-download url target-dir file-path)
                 :reducer (fn [_ctx _x]
                            nil)}]}))

(defn download
  [{:keys [name url directory]}]
  (let [extname (.extname path (url->path url))
        basename (str (.basename path name extname) extname)
        target-dir (.resolve path (js/process.cwd) (.join path "public" "assets" directory))
        file-path (.join path target-dir basename)
        url-path (.join path "/assets" directory basename)]

    #_(enqueue-download url target-dir file-path)
    (fetch-download url target-dir file-path)
    url-path))

(defn fetch-image
  [project directory url & {:keys [name]}]
  (p/catch
    (p/promise
      (download
        {:url  url
         :directory directory
         :name (or name (:slug project))}))
    (fn [error]
      (js/console.warn (str "Failed to fetch image url " url " for " (name (:type project)) " " (:title project)))
      (js/console.error error)
      {})))

