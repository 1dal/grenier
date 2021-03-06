import unittest
import getpass
import shutil
from grenier.helpers import *
from grenier.grenier import Grenier


class TestClass(unittest.TestCase):
    def setUp(self):
        self.grenier = Grenier(Path("test_files", "test.yaml"))
        self.grenier.open_config()
        print()

    def tearDown(self):
        del self.grenier

    def test_010_open_config(self):
        # resetting config
        self.grenier.repositories = []
        self.assertTrue(self.grenier.open_config())
        self.assertIsNotNone(self.grenier.repositories)
        self.assertEqual(len(self.grenier.repositories), 2)

        for test_repo in self.grenier.repositories:
            self.assertIn(test_repo.name, ["test1", "test2"])
            if test_repo.name == "test1":
                self.assertEqual(test_repo.backend.name, "bup")
                self.assertEqual(test_repo.repository_path, Path("test_files/backup/grenier_test1"))
            elif test_repo.name == "test2":
                self.assertEqual(test_repo.backend.name, "restic")
                self.assertEqual(test_repo.repository_path, Path("test_files/backup/grenier_test2"))

            # repositories
            self.assertTrue(test_repo.repository_path.exists())
            self.assertEqual(test_repo.passphrase, "test")

            # sources
            self.assertEqual(len(test_repo.sources), 2)
            for source in test_repo.sources:
                self.assertIn(source.name, ["folder1", "folder2"])
                if source.name == "folder1":
                    self.assertEqual(source.target_dir, Path("test_files/folder1"))
                    self.assertListEqual(source.excluded_extensions, ["ignored"])
                else:
                    self.assertEqual(source.target_dir, Path("test_files/folder2"))
                    self.assertListEqual(source.excluded_extensions, [])

            # remotes
            self.assertEqual(len(test_repo.remotes), 4)

    def test_015_init(self):
        for r in self.grenier.repositories:
            success, err_log = r.init(display=False)
            self.assertTrue(success)

            # test not empty
            repo_contents = [str(el) for el in r.repository_path.rglob("*")]
            self.assertNotEqual(len(repo_contents), 0)
            # TODO better tests?

            # cleanup
            shutil.rmtree(str(r.repository_path))

    def test_020_save(self):
        for r in self.grenier.repositories:
            print("Saving %s" % r.name)
            success, output = r.save(display=False)
            self.assertTrue(success)

            repo_contents = [str(el) for el in r.repository_path.rglob("*")]
            self.assertNotEqual(len(repo_contents), 0)

    def test_030_fuse(self):
        for r in self.grenier.repositories:
            print("Mounting %s" % r.name)
            r.fuse(r.temp_dir, display=False)
            fuse_contents = [str(el.relative_to(r.temp_dir)) for el in r.temp_dir.rglob("*")]
            self.assertNotEqual(len(fuse_contents), 0)
            for s in r.sources:
                self.assertTrue(s.name in fuse_contents)
                # verifying contents
                if s.name == "folder1":
                    self.assertTrue("folder1/latest/test1.txt" in fuse_contents)
                    self.assertFalse("folder1/latest/test2.ignored" in fuse_contents)
                if s.name == "folder2":
                    self.assertTrue("folder2/latest/test3.txt" in fuse_contents)
                    self.assertTrue("folder2/latest/test4.ignored" in fuse_contents)

    def test_040_unfuse(self):
        for r in self.grenier.repositories:
            r.unfuse(r.temp_dir, display=False)
            fuse_contents = [str(el) for el in r.temp_dir.rglob("*")]
            self.assertEqual(len(fuse_contents), 0)
            self.assertFalse(is_fuse_mounted(r.temp_dir))

    def test_050_check(self):
        for r in self.grenier.repositories:
            print("Checking %s" % r.name)
            success, out = r.check_and_repair(display=False)
            self.assertTrue(success)
            # TODO corrupt one file and check again!!

    def test_060_sync_to_folder(self):
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))
            remote_path = Path("/tmp/grenier")
            self.assertTrue(r.sync_remote(str(remote_path), display=False))
            self.assertTrue(remote_path.exists())
            contents = [str(el) for el in remote_path.rglob("*")]
            self.assertNotEqual(len(contents), 0)
            # TODO other checks?
            # check sync yaml
            last_synced_yaml = Path(remote_path, "last_synced.yaml")
            self.assertTrue(last_synced_yaml.exists())
            # TODO check contents?

            # cleanup
            shutil.rmtree(str(remote_path))

    def test_070_sync_to_disk(self):
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))

            # needs external disk connected, skip if not present
            remote_path = Path("/run/media/%s/%s" % (getpass.getuser(), "DISK1"))
            if remote_path.exists():
                self.assertTrue(r.sync_remote("DISK1", display=False))

                contents = [str(el) for el in remote_path.rglob("*")]
                self.assertNotEqual(len(contents), 0)

                # TODO other checks?
                # check sync yaml
                last_synced_yaml = Path(remote_path, "last_synced.yaml")
                self.assertTrue(last_synced_yaml.exists())
                # TODO check contents?

                # TODO cleanup

    def test_080_sync_to_hubic(self):
        # needs rclone config "test_cloud_container"
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("pof", display=False))

            remote = r._find_remote_by_name("test_cloud_container")
            self.assertIsNotNone(remote)
            self.assertTrue(remote.is_known)
            self.assertTrue(remote.is_cloud)

            self.assertTrue(r.sync_remote("test_cloud_container", display=False))
            if r.name == "test1":
                # testing encfs xml backup
                xml = Path(xdg.BaseDirectory.save_data_path("grenier"), "encfs_xml", "%s.xml" % r.name)
                self.assertTrue(xml.exists())
            # TODO test remote file size vs local?

            # TODO cleanup: rclone purge test_cloud_container:test1?

    def test_100_sync_to_undefined_cloud(self):
        for r in self.grenier.repositories:
            self.assertFalse(r.sync_remote("fake_cloud", display=False))

    def test_110_restore_files_from_repository(self):
        restore_path = Path("test_files/restore")
        for r in self.grenier.repositories:
            print("Restoring %s." % r.name)
            success, output = r.restore(restore_path, display=False)
            self.assertTrue(success)

            # testing restored files
            restored = [str(el.relative_to(restore_path)) for el in restore_path.rglob("*")]
            self.assertIn("folder1", restored)
            self.assertIn("folder2", restored)
            self.assertIn("folder1/test1.txt", restored)
            self.assertIn("folder2/test3.txt", restored)
            self.assertIn("folder2/test4.ignored", restored)
            # testing contents of one file
            self.assertEqual(Path(restore_path, "folder1", "test1.txt").read_text(), "1234567890")

            # cleanup
            shutil.rmtree(str(restore_path))

    def test_115_recover_files_from_remote_folder(self):
        for r in self.grenier.repositories:
            print("Recovering %s." % r.name)
            # copying before test
            remote_path = Path("/tmp/grenier")
            self.assertTrue(r.sync_remote(str(remote_path), display=False))
            # recover what was just rsynced
            success, err_log = r.recover(remote_path, r.temp_dir, display=False)
            self.assertTrue(success)
            self.assertEqual(err_log, "")

            # check files
            original = [str(el.relative_to(remote_path)) for el in remote_path.rglob("*")
                        if str(el.relative_to(remote_path)) != "last_synced.yaml"]
            recovered = [str(el.relative_to(r.temp_dir)) for el in r.temp_dir.rglob("*")]

            diff1 = [el for el in original if el not in recovered]
            diff2 = [el for el in recovered if el not in original]
            self.assertEqual(diff1, [])
            self.assertEqual(diff2, [])

            # cleanup
            shutil.rmtree(str(r.temp_dir))
            shutil.rmtree(str(remote_path))

    def test_120_recover_files_from_remote_cloud(self):
        restore_path = Path("test_files", "restore_cloud")
        for r in self.grenier.repositories:
            print("Recovering %s." % r.name)
            success, output = r.recover("test_cloud_container",
                                        restore_path,
                                        display=False)
            self.assertTrue(success)

            # check files
            recovered = [str(el.relative_to(restore_path)) for el in restore_path.rglob("*")]
            self.assertNotEqual(recovered, [])
            if r.name == "test1":
                self.assertTrue("bupindex" in recovered)
            elif r.name == "test2":
                self.assertTrue("config" in recovered)

            #  cleanup
            umount(restore_path)
            shutil.rmtree(str(restore_path))
            shutil.rmtree(str(r.temp_dir))

    def test_130_list(self):
        # TODO!
        pass


if __name__ == '__main__':
    unittest.main()
