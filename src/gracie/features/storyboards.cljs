(ns gracie.features.storyboards
  (:require
    [promesa.core :as p]
    [gracie.data-pipeline :refer [defhook]]
    [framework.utils :as u]
    ["path" :as path]
    ["stream" :refer [Readable]]
    ["fs" :as fs]))

(defhook :storyboards :parse-project
  (fn storyboards-parse-project
    [original-project]
    {:id               (get-in original-project [:properties :formula :string])
     :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
     :published        (= (get-in original-project [:properties :published :checkbox]) true)
     :title            (get-in original-project [:properties :name :title 0 :text :content])
     :category         (get-in original-project [:properties :select :name])
     :vimeo-url        (get-in original-project [:properties :vimeo-url :url])
     :thumbnail-url    (get-in original-project [:properties :thumbnail :files 0 :file :url])
     :speakerdeck-urls (->> (get-in original-project [:properties :speakerdeck-url :files])
                            (map #(get-in % [:external :url])))
     :pdf-urls         (->> (get-in original-project [:properties :thumbnail :files])
                            (map #(get-in % [:file :url])))}))


(defn fetch-vimeo-oembed
  [project url]
  (let [vimeo-api-url (str "https://vimeo.com/api/oembed.json?url="
                           (js/encodeURIComponent url)
                           "&width=1280&height=720")
        params {:headers {"Referer"
                          "https://gracieanimator.squarespace.com"}}
        request (js/fetch vimeo-api-url (clj->js params))]
    (p/catch
      (p/-> request
            (.json)
            (js->clj :keywordize-keys true)
            (update :thumbnail_url #(str % ".jpg")))
      (fn [error]
        (js/console.warn "Failed to fetch vimeo url" url " for storyboard" (:title project))
        (js/console.error error)
        {}))))

(defn fetch-speakerdeck-oembed
  [project url]
  (let [vimeo-api-url (str "https://speakerdeck.com/oembed.json?url="
                           (js/encodeURIComponent url))
        request (js/fetch vimeo-api-url)]
    (p/catch
      (p/-> request
            (.json)
            (js->clj :keywordize-keys true))
      (fn [error]
        (js/console.warn "Failed to fetch speakerdeck url" url "for storyboard" (:title project))
        (js/console.error error)
        {}))))

(defn download-asset
  [{:keys [url type directory name]} request]
  (->> (.fromWeb Readable (.-body request))
       (.pipe (fs/createWriteStream
                (.join path "assets" type directory name
                       (.extname path url))))))

(defn fetch-image
  [project image-type url]
  (p/catch
    (p/-> (js/fetch url)
          (download-asset
           {:url  url
            :type (:type project)
            :directory image-type
            :name (u/slugify (:title project))}))
    (fn [error]
      (js/console.warn "Failed to fetch image url" url "for storyboard" (:title project))
      (js/console.error error)
      {})))

(defhook :storyboards :queue-requests
  (fn storyboards-queue-requests
    [project]
    (concat
      []
      (when-let [vimeo-url (:vimeo-url project)]
        [{:url vimeo-url
          :fetch #(fetch-vimeo-oembed project %)}])
      (when-let [speakerdeck-urls (seq (:speakerdeck-urls project))]
        (for [speakerdeck-url speakerdeck-urls]
          {:url speakerdeck-url
           :fetch #(fetch-speakerdeck-oembed project %)}))
      (when-let [thumbnail-url (:thumbnail-url project)]
        [{:url thumbnail-url
          :fetch #(fetch-image project "thumbnails" %)}]))))


(defhook :storyboards :queue-requests
  (fn storyboards-queue-requests
    [project]
    (let [vimeo-oembed (vimeo-request project)])))
