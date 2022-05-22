(ns workers.download
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [clojure.string :as s]
   ["path" :as path]
   ["node-fetch$default" :as fetch]
   ["fs" :as fs]))

(defn normalize-filename
  [filename basename]
  (cond (and filename
             (s/includes? filename "."))
        filename

        filename
        (str filename (.extname path basename))

        :else
        basename))


(let [{:keys [url dir filename root]} (js->clj
                                       (js/JSON.parse (nth js/process.argv 3))
                                       :keywordize-keys true)
      url-obj (js/URL. url)
      url-path (.-pathname url-obj)
      base (normalize-filename filename (.basename path url-path))
      dest-file (.join path root dir base)
      dest-url (.join path dir base)]
  (.mkdirSync fs (.join path root dir) #js {:recursive true})
  (let [dest-stream (.createWriteStream fs dest-file)]
    (p/let [res (fetch url)]
      (-> (js/Promise.
             (fn [resolve]
               (.once
                dest-stream "finish" (fn []
                                       (resolve (str "/" dest-url))))
               (.pipe (.-body res) dest-stream)))
          (p/then println)
          (p/catch
              (fn [err]
                (js/console.error "Failed downloading" url)
                (js/console.error err)
                (js/throw err)))))))
